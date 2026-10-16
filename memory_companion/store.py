"""Deterministic memory lifecycle; the model never writes this database directly."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import uuid


KINDS = {"preference", "decision", "handoff", "incident", "procedure"}
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}\Z")
FORMAT = "homelab-memory-v1"


class Conflict(ValueError):
    """A record changed since the user inspected it."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def text(value, name, maximum, empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
        raise ValueError(f"{name} must be {'0' if empty else '1'}–{maximum} characters.")
    return value.strip()


def slug(value):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise ValueError("Use a lowercase identifier of up to 80 letters, digits, dashes, or underscores.")
    return value


def timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expiry must be a timezone-aware ISO date/time or null.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Expiry must be a timezone-aware ISO date/time.") from exc
    if parsed.tzinfo is None:
        raise ValueError("Expiry needs an explicit timezone.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def validate_metadata(kind, metadata):
    if not isinstance(metadata, dict) or len(json.dumps(metadata, allow_nan=False)) > 20000:
        raise ValueError("Metadata must be a JSON object of at most 20,000 characters.")
    if kind == "procedure":
        steps = metadata.get("steps", [])
        version = metadata.get("version", 1)
        if type(version) is not int or version < 1:
            raise ValueError("Procedure version must be a positive integer.")
        if not isinstance(steps, list) or len(steps) > 50:
            raise ValueError("A procedure supports at most 50 steps.")
        for step in steps:
            if not isinstance(step, dict) or set(step) - {"instruction", "state", "evidence"}:
                raise ValueError("Invalid procedure step.")
            text(step.get("instruction"), "Step instruction", 1000)
            if step.get("state", "pending") not in {"pending", "attempted", "confirmed"}:
                raise ValueError("Invalid step state.")
            evidence = text(step.get("evidence", ""), "Step evidence", 2000, empty=True)
            if step.get("state") == "confirmed" and not evidence:
                raise ValueError("A confirmed step requires evidence or an explicit user confirmation note.")
    return metadata


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("Unsupported database version; open with a matching companion release.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projects(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS aliases(
                    alias TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id));
                CREATE TABLE IF NOT EXISTS memories(
                    id TEXT PRIMARY KEY, scope TEXT NOT NULL, kind TEXT NOT NULL,
                    key TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL,
                    metadata TEXT NOT NULL, revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, expires_at TEXT,
                    UNIQUE(scope, kind, key));
                CREATE TABLE IF NOT EXISTS audit(
                    event_id INTEGER PRIMARY KEY, at TEXT NOT NULL,
                    action TEXT NOT NULL, record_id TEXT NOT NULL, revision INTEGER);
                CREATE TABLE IF NOT EXISTS proposals(
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA secure_delete=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def projects(self):
        with self.db() as db:
            return [dict(row) for row in db.execute("SELECT * FROM projects ORDER BY name")]

    def resolve(self, project, db=None):
        slug(project)
        if db is None:
            with self.db() as connection:
                return self.resolve(project, connection)
        row = db.execute("SELECT id FROM projects WHERE id=?", (project,)).fetchone()
        if row:
            return row[0]
        row = db.execute("SELECT project FROM aliases WHERE alias=?", (project,)).fetchone()
        if row:
            return row[0]
        raise ValueError("Unknown project; create or select an existing project.")

    def project(self, identifier, name, aliases=()):
        slug(identifier)
        name = text(name, "Project name", 100)
        if not isinstance(aliases, (list, tuple)) or len(aliases) > 50:
            raise ValueError("At most 50 aliases are supported.")
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM aliases WHERE alias=?", (identifier,)).fetchone():
                raise Conflict("That identifier is already an alias.")
            db.execute("INSERT INTO projects VALUES(?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",
                       (identifier, name))
            for alias in aliases:
                slug(alias)
                if alias == identifier:
                    continue
                if db.execute("SELECT 1 FROM projects WHERE id=?", (alias,)).fetchone():
                    raise Conflict("An alias cannot replace another project identity.")
                old = db.execute("SELECT project FROM aliases WHERE alias=?", (alias,)).fetchone()
                if old and old[0] != identifier:
                    raise Conflict("That alias belongs to another project.")
                db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?)", (alias, identifier))
        return {"id": identifier, "name": name}

    def scope(self, scope, db):
        if scope == "global":
            return scope
        if isinstance(scope, str) and scope.startswith("project:"):
            return "project:" + self.resolve(scope[8:], db)
        raise ValueError("Scope must be global or project:<identifier>.")

    @staticmethod
    def record(row):
        if row is None:
            raise ValueError("Memory not found.")
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        return result

    def get(self, identifier, db=None):
        if db is None:
            with self.db() as connection:
                return self.get(identifier, connection)
        return self.record(db.execute("SELECT * FROM memories WHERE id=?", (identifier,)).fetchone())

    def _put(self, db, *, scope, kind, key, content, source, metadata=None,
             expected_revision=0, expires_at=None):
        scope = self.scope(scope, db)
        if kind not in KINDS:
            raise ValueError("Unknown memory kind.")
        slug(key)
        content = text(content, "Memory", 12000)
        source = text(source, "Source", 2000)
        metadata = validate_metadata(kind, {} if metadata is None else metadata)
        expiry = timestamp(expires_at)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("Expected revision must be a nonnegative integer.")
        old = db.execute("SELECT * FROM memories WHERE scope=? AND kind=? AND key=?", (scope, kind, key)).fetchone()
        if (old["revision"] if old else 0) != expected_revision:
            raise Conflict("This memory changed. Inspect the latest revision before saving.")
        identifier = old["id"] if old else uuid.uuid4().hex
        revision = expected_revision + 1
        updated = now()
        created = old["created_at"] if old else updated
        db.execute("""INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET content=excluded.content,source=excluded.source,
            metadata=excluded.metadata,revision=excluded.revision,
            updated_at=excluded.updated_at,expires_at=excluded.expires_at""",
            (identifier, scope, kind, key, content, source, json.dumps(metadata, allow_nan=False),
             revision, created, updated, expiry))
        db.execute("INSERT INTO audit(at,action,record_id,revision) VALUES(?,?,?,?)",
                   (updated, "replace" if old else "save", identifier, revision))
        return self.get(identifier, db)

    def put(self, **fields):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            return self._put(db, **fields)

    def forget(self, identifier, expected_revision):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.get(identifier, db)
            if type(expected_revision) is not int or row["revision"] != expected_revision:
                raise Conflict("Memory changed; inspect its current revision before forgetting.")
            db.execute("DELETE FROM memories WHERE id=?", (identifier,))
            # Proposals can contain the old content. Clear pending proposals on every delete.
            db.execute("DELETE FROM proposals")
            db.execute("INSERT INTO audit(at,action,record_id,revision) VALUES(?,?,?,?)",
                       (now(), "forget", identifier, expected_revision))
        return {"forgotten": identifier, "pending_proposals_cleared": True}

    def list(self, project, include_expired=False):
        with self.db() as db:
            project = self.resolve(project, db)
            rows = db.execute("SELECT * FROM memories WHERE scope IN (?,?) ORDER BY updated_at DESC,id",
                              ("global", "project:" + project)).fetchall()
            return [self.record(row) for row in rows
                    if include_expired or row["expires_at"] is None or row["expires_at"] > now()]

    def select(self, project, query, budget=10000):
        text(query, "Question", 12000)
        if type(budget) is not int or not 500 <= budget <= 20000:
            raise ValueError("Context budget must be 500–20,000 characters.")
        rows = self.list(project)
        # A project preference overrides a global preference only when both have the same key.
        overridden = {row["key"] for row in rows if row["kind"] == "preference" and row["scope"] != "global"}
        tokens = set(re.findall(r"[a-z0-9_]+", query.lower())) - {
            "the", "a", "an", "is", "it", "and", "to", "of", "for", "what", "how", "my", "our"}
        candidates = []
        excluded = []
        for row in rows:
            if row["kind"] == "preference" and row["scope"] == "global" and row["key"] in overridden:
                excluded.append({"id": row["id"], "reason": "project preference overrides same global key"})
                continue
            searchable = set(re.findall(r"[a-z0-9_]+", (row["key"] + " " + row["content"] + " " + json.dumps(row["metadata"])).lower()))
            score = len(tokens & searchable)
            if row["kind"] in {"preference", "handoff"}:
                score += 2
            if not score:
                excluded.append({"id": row["id"], "reason": "no keyword match"})
                continue
            candidates.append((score, row))
        candidates.sort(key=lambda pair: (-pair[0], -datetime.fromisoformat(pair[1]["updated_at"]).timestamp(), pair[1]["id"]))
        selected, used = [], 0
        for score, row in candidates:
            candidate = {**row, "selection_reason": "active preference/handoff or keyword overlap", "score": score}
            cost = len(json.dumps(candidate, ensure_ascii=False))
            if used + cost > budget:
                excluded.append({"id": row["id"], "reason": "context budget"})
                continue
            selected.append(candidate)
            used += cost
        return {"records": selected, "excluded": excluded, "characters": used, "budget": budget,
                "project": self.resolve(project)}

    def propose(self, fields):
        # Validate against current state in a transaction, then roll back the trial write.
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("SAVEPOINT trial")
            self._put(db, **fields)
            db.execute("ROLLBACK TO trial")
            db.execute("RELEASE trial")
            identifier = uuid.uuid4().hex
            db.execute("INSERT INTO proposals VALUES(?,?,?)", (identifier, json.dumps(fields, allow_nan=False), now()))
        return {"id": identifier, "fields": fields, "status": "pending_review"}

    def proposals(self):
        with self.db() as db:
            return [{"id": row["id"], "fields": json.loads(row["payload"]), "created_at": row["created_at"]}
                    for row in db.execute("SELECT * FROM proposals ORDER BY created_at")]

    def review(self, identifier, approve):
        if type(approve) is not bool:
            raise ValueError("Review decision must be true or false.")
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM proposals WHERE id=?", (identifier,)).fetchone()
            if not row:
                raise ValueError("Proposal not found or already reviewed.")
            if (datetime.now(timezone.utc) - datetime.fromisoformat(row["created_at"])).total_seconds() > 3600:
                raise Conflict("Proposal expired; generate and review a fresh proposal.")
            result = self._put(db, **json.loads(row["payload"])) if approve else {"rejected": identifier}
            db.execute("DELETE FROM proposals WHERE id=?", (identifier,))
            return result

    def step(self, identifier, index, state, evidence, expected_revision):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            record = self.get(identifier, db)
            if record["kind"] != "procedure" or type(index) is not int:
                raise ValueError("Choose a procedure step.")
            steps = record["metadata"].get("steps", [])
            if not 0 <= index < len(steps):
                raise ValueError("Step index is out of range.")
            steps[index].update(state=state, evidence=evidence)
            return self._put(db, **{field: record[field] for field in
                ("scope", "kind", "key", "content", "source", "metadata", "expires_at")},
                expected_revision=expected_revision)

    def export(self):
        with self.db() as db:
            return {"format": FORMAT, "exported_at": now(),
                    "projects": [dict(row) for row in db.execute("SELECT * FROM projects ORDER BY id")],
                    "aliases": [dict(row) for row in db.execute("SELECT * FROM aliases ORDER BY alias")],
                    "memories": [self.record(row) for row in db.execute("SELECT * FROM memories ORDER BY id")]}

    def import_data(self, document, apply=False):
        if not isinstance(document, dict) or document.get("format") != FORMAT:
            raise ValueError("Unknown export format.")
        if len(json.dumps(document, allow_nan=False)) > 1_000_000:
            raise ValueError("Import exceeds 1 MB.")
        if type(apply) is not bool:
            raise ValueError("Apply must be a boolean.")
        projects, aliases, records = (document.get(name) for name in ("projects", "aliases", "memories"))
        if not all(isinstance(items, list) for items in (projects, aliases, records)):
            raise ValueError("Export collections must be lists.")
        if len(projects) > 100 or len(aliases) > 500 or len(records) > 2000:
            raise ValueError("Import collection limits exceeded.")
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] or db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]:
                raise Conflict("Import requires an empty destination. Use a fresh data directory.")
            for project in projects:
                db.execute("INSERT INTO projects VALUES(?,?)", (slug(project["id"]), text(project["name"], "Project name", 100)))
            for alias in aliases:
                alias_id = slug(alias["alias"])
                if db.execute("SELECT 1 FROM projects WHERE id=?", (alias_id,)).fetchone():
                    raise Conflict("Alias collides with project identity.")
                db.execute("INSERT INTO aliases VALUES(?,?)", (alias_id, self.resolve(alias["project"], db)))
            seen, seen_ids = set(), set()
            for record in records:
                identity = (record["scope"], record["kind"], record["key"])
                if identity in seen:
                    raise Conflict("Duplicate memory key in import.")
                seen.add(identity)
                original_id = record.get("id")
                revision = record.get("revision")
                if not isinstance(original_id, str) or not re.fullmatch(r"[0-9a-f]{32}", original_id) or original_id in seen_ids:
                    raise ValueError("Import record IDs must be unique 32-character lowercase hex identifiers.")
                if type(revision) is not int or revision < 1:
                    raise ValueError("Imported revision must be a positive integer.")
                created, updated = timestamp(record.get("created_at")), timestamp(record.get("updated_at"))
                if not created or not updated or created > updated:
                    raise ValueError("Imported timestamps are missing or inconsistent.")
                seen_ids.add(original_id)
                inserted = self._put(db, **{field: record[field] for field in
                    ("scope", "kind", "key", "content", "source", "metadata", "expires_at")}, expected_revision=0)
                db.execute("UPDATE memories SET id=?,revision=?,created_at=?,updated_at=? WHERE id=?",
                           (original_id, revision, created, updated, inserted["id"]))
                db.execute("UPDATE audit SET record_id=?,revision=? WHERE record_id=?", (original_id, revision, inserted["id"]))
            result = {"projects": len(projects), "memories": len(records), "applied": apply,
                      "notice": "Record IDs and revisions are preserved; previously deleted data may return from old exports. Review restored context before use."}
            if not apply:
                db.rollback()
            return result

    def backup(self, destination):
        destination = Path(destination)
        if destination.resolve() == self.path.resolve() or destination.exists():
            raise ValueError("Choose a new backup path, separate from the live database.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(destination)
        try:
            with self.db() as source:
                source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed.")
        finally:
            target.close()
        return {"backup": destination.name, "notice": "Backups contain memory content. Store privately; old backups can restore forgotten records."}

    def integrity(self):
        with self.db() as db:
            return db.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and not db.execute("PRAGMA foreign_key_check").fetchall()
