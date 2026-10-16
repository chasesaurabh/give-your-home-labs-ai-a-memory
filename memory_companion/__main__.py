import argparse
import json
from pathlib import Path
import sqlite3

from .store import Store
from .server import serve


def main():
    parser = argparse.ArgumentParser(description="Inspectable local AI memory companion")
    parser.add_argument("--data", default="data/memory.sqlite", help="Database path, including filename")
    commands = parser.add_subparsers(dest="command", required=True)
    web = commands.add_parser("serve")
    web.add_argument("--port", type=int, default=8765)
    commands.add_parser("doctor")
    project = commands.add_parser("project")
    project.add_argument("id")
    project.add_argument("name")
    project.add_argument("--alias", action="append", default=[])
    save = commands.add_parser("save")
    save.add_argument("scope")
    save.add_argument("kind")
    save.add_argument("key")
    save.add_argument("content")
    save.add_argument("--source", required=True)
    save.add_argument("--revision", type=int, default=0)
    save.add_argument("--metadata", default="{}")
    save.add_argument("--expires")
    listing = commands.add_parser("list")
    listing.add_argument("project")
    listing.add_argument("--include-expired", action="store_true")
    forget = commands.add_parser("forget")
    forget.add_argument("id")
    forget.add_argument("revision", type=int)
    selection = commands.add_parser("select")
    selection.add_argument("project")
    selection.add_argument("question")
    export = commands.add_parser("export")
    export.add_argument("file")
    importing = commands.add_parser("import")
    importing.add_argument("file")
    importing.add_argument("--apply", action="store_true")
    backup = commands.add_parser("backup")
    backup.add_argument("file")
    restore = commands.add_parser("restore")
    restore.add_argument("file")
    args = parser.parse_args()
    try:
        if args.command == "serve":
            serve(args.data, args.port)
            return
        if args.command == "restore":
            destination = Path(args.data)
            source = Path(args.file)
            if destination.exists() or not source.is_file():
                raise ValueError("Restore needs an existing backup and a new destination database path.")
            connection = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup failed integrity check.")
                if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                    raise ValueError("Backup format is not supported by this release.")
                expected = {"projects", "aliases", "memories", "audit", "proposals"}
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not expected <= tables:
                    raise ValueError("Backup is missing companion tables.")
                if connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Backup has broken relationships.")
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Use SQLite's backup API: a raw file copy can omit journaled data.
                target = sqlite3.connect(destination)
                try:
                    connection.backup(target)
                finally:
                    target.close()
            finally:
                connection.close()
            print(json.dumps({"restored": destination.name, "notice": "Review old memories before using this restored store; deleted records may return."}))
            return
        store = Store(args.data)
        if args.command == "doctor":
            from . import __version__
            from .model import Model
            import sys
            result = {"version": __version__, "python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
                      "integrity": store.integrity(), "projects": len(store.projects()), "model": Model().info(),
                      "notice": "Configuration check only; it does not make an inference request."}
        elif args.command == "project":
            result = store.project(args.id, args.name, args.alias)
        elif args.command == "save":
            result = store.put(scope=args.scope, kind=args.kind, key=args.key, content=args.content,
                               source=args.source, expected_revision=args.revision,
                               metadata=json.loads(args.metadata), expires_at=args.expires)
        elif args.command == "list":
            result = store.list(args.project, args.include_expired)
        elif args.command == "forget":
            result = store.forget(args.id, args.revision)
        elif args.command == "select":
            result = store.select(args.project, args.question)
        elif args.command == "export":
            target = Path(args.file)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as file:
                json.dump(store.export(), file, ensure_ascii=False, indent=2)
            result = {"exported": target.name, "notice": "Contains memory content; store privately."}
        elif args.command == "import":
            target = Path(args.file)
            if target.stat().st_size > 1_000_000:
                raise ValueError("Import exceeds 1 MB.")
            result = store.import_data(json.loads(target.read_text(encoding="utf-8")), args.apply)
        else:
            result = store.backup(args.file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError) as exc:
        parser.exit(2, f"Companion operation failed: {exc}\n")


if __name__ == "__main__":
    main()
