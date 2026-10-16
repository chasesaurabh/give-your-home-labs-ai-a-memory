from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from memory_companion.model import Model, local_url, messages_for, suggest, citation_check
from memory_companion.server import make_server
from memory_companion.store import Store, Conflict


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.store = Store(self.path / "memory.sqlite")
        self.store.project("reading-desk", "Reading Desk", ["shelf"])
        self.store.project("lab-journal", "Lab Journal")

    def save(self, **changes):
        fields = dict(scope="project:reading-desk", kind="preference", key="style",
                      content="Prefer concise replies.", source="Explicit synthetic instruction")
        return self.store.put(**{**fields, **changes})

    def test_data_persists_through_an_independent_cli_process(self):
        self.save()
        output = subprocess.run([sys.executable, "-m", "memory_companion", "--data", str(self.store.path),
                                 "list", "reading-desk"], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(output.stdout)[0]["content"], "Prefer concise replies.")

    def test_alias_and_display_name_do_not_create_a_second_project(self):
        self.store.project("reading-desk", "Reading Desk Revised", ["shelf"])
        self.save()
        self.assertEqual(self.store.resolve("shelf"), "reading-desk")
        self.assertEqual(len(self.store.projects()), 2)
        self.assertEqual(self.store.list("shelf"), self.store.list("reading-desk"))

    def test_alias_cannot_take_over_another_project(self):
        with self.assertRaises(Conflict):
            self.store.project("reading-desk", "Renamed", ["lab-journal"])
        self.assertEqual(self.store.projects()[1]["name"], "Reading Desk")

    def test_other_project_never_enters_context(self):
        own = self.save()
        self.save(scope="project:lab-journal", content="A unique confidential distractor: ORCHID.")
        selection = self.store.select("reading-desk", "ORCHID preference")
        self.assertEqual([x["id"] for x in selection["records"]], [own["id"]])
        self.assertNotIn("ORCHID", json.dumps(selection))

    def test_project_preference_overrides_global_same_key(self):
        global_record = self.save(scope="global", content="Detailed replies")
        local = self.save(content="Brief replies")
        selected = self.store.select("reading-desk", "Describe this")
        self.assertEqual([x["id"] for x in selected["records"]], [local["id"]])
        self.assertEqual(selected["excluded"][0]["id"], global_record["id"])

    def test_stale_edit_does_not_overwrite_current_content(self):
        old = self.save()
        current = self.save(expected_revision=old["revision"], content="Use a table.")
        with self.assertRaises(Conflict):
            self.save(expected_revision=old["revision"], content="Stale text")
        self.assertEqual(self.store.get(current["id"])["content"], "Use a table.")

    def test_invalid_edit_rolls_back(self):
        old = self.save()
        with self.assertRaises(ValueError):
            self.save(expected_revision=old["revision"], content="")
        self.assertEqual(self.store.get(old["id"])["revision"], 1)

    def test_expiry_filters_retrieval_but_remains_inspectable(self):
        expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.save(expires_at=expired)
        self.assertEqual(self.store.select("reading-desk", "style")["records"], [])
        self.assertEqual(len(self.store.list("reading-desk", True)), 1)

    def test_expiry_needs_a_timezone(self):
        with self.assertRaises(ValueError):
            self.save(expires_at="2026-01-01T00:00:00")

    def test_forget_removes_context_and_pending_copies(self):
        record = self.save(content="Synthetic secret phrase LARCH")
        self.store.propose(dict(scope=record["scope"], kind=record["kind"], key=record["key"],
            content="Synthetic secret phrase LARCH revised", source="review", expected_revision=1))
        self.store.forget(record["id"], 1)
        self.assertEqual(self.store.select("reading-desk", "LARCH")["records"], [])
        self.assertEqual(self.store.proposals(), [])
        self.assertNotIn("LARCH", json.dumps(self.store.export()))
        with self.store.db() as db:
            self.assertNotIn("LARCH", json.dumps([tuple(row) for row in db.execute("SELECT * FROM audit")]))

    def test_stale_forget_rejected(self):
        record = self.save()
        self.save(expected_revision=1, content="New preference")
        with self.assertRaises(Conflict):
            self.store.forget(record["id"], 1)
        self.assertEqual(len(self.store.list("reading-desk")), 1)

    def test_no_match_does_not_supply_an_unrelated_incident(self):
        self.save(kind="incident", key="port", content="An incorrect port prevented connection.")
        self.assertEqual(self.store.select("reading-desk", "Which GPU was purchased?")["records"], [])

    def test_context_budget_does_not_truncate_half_a_record(self):
        self.save(content="x" * 3000)
        result = self.store.select("reading-desk", "style", budget=500)
        self.assertEqual(result["records"], [])
        self.assertEqual(result["excluded"][0]["reason"], "context budget")

    def test_proposal_does_not_write_until_reviewed(self):
        fields = dict(scope="project:reading-desk", kind="preference", key="shell", content="Use PowerShell", source="explicit")
        proposal = self.store.propose(fields)
        self.assertEqual(self.store.list("reading-desk"), [])
        self.store.review(proposal["id"], True)
        self.assertEqual(self.store.list("reading-desk")[0]["content"], "Use PowerShell")
        with self.assertRaises(ValueError):
            self.store.review(proposal["id"], True)

    def test_rejected_proposal_leaves_no_memory(self):
        proposal = self.store.propose(dict(scope="project:reading-desk", kind="preference", key="shell", content="Use Bash", source="explicit"))
        self.store.review(proposal["id"], False)
        self.assertEqual(self.store.list("reading-desk"), [])
        self.assertEqual(self.store.proposals(), [])

    def test_proposal_cannot_overwrite_a_later_edit(self):
        record = self.save()
        proposal = self.store.propose(dict(scope=record["scope"], kind="preference", key="style", content="Proposed", source="review", expected_revision=1))
        self.save(expected_revision=1, content="Later approved edit")
        with self.assertRaises(Conflict):
            self.store.review(proposal["id"], True)
        self.assertEqual(self.store.get(record["id"])["content"], "Later approved edit")

    def test_expired_proposal_cannot_be_approved(self):
        proposal = self.store.propose(dict(scope="global", kind="preference", key="style", content="Brief", source="explicit"))
        with self.store.db() as db:
            db.execute("UPDATE proposals SET created_at=?", ((datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(),))
        with self.assertRaises(Conflict):
            self.store.review(proposal["id"], True)

    def test_procedure_states_require_evidence_and_survive_restart(self):
        record = self.save(kind="procedure", key="document-service", content="Document a service", metadata={"version": 2, "steps": [
            {"instruction": "Record purpose", "state": "pending", "evidence": ""},
            {"instruction": "Verify restore", "state": "attempted", "evidence": "Rehearsal started"}]})
        with self.assertRaises(ValueError):
            self.store.step(record["id"], 0, "confirmed", "", 1)
        self.store.step(record["id"], 0, "confirmed", "User confirmed documentation exists", 1)
        reopened = Store(self.store.path).get(record["id"])
        self.assertEqual(reopened["metadata"]["version"], 2)
        self.assertEqual(reopened["metadata"]["steps"][1]["state"], "attempted")

    def test_import_preview_has_no_effect_and_apply_preserves_meaning(self):
        self.save()
        document = self.store.export()
        fresh = Store(self.path / "import.sqlite")
        self.assertFalse(fresh.import_data(document)["applied"])
        self.assertEqual(fresh.projects(), [])
        fresh.import_data(document, True)
        self.assertEqual(fresh.resolve("shelf"), "reading-desk")
        self.assertEqual(fresh.list("reading-desk")[0]["content"], "Prefer concise replies.")
        self.assertEqual(fresh.list("reading-desk")[0]["id"], document["memories"][0]["id"])
        self.assertEqual(fresh.list("reading-desk")[0]["revision"], document["memories"][0]["revision"])
        self.assertTrue(fresh.integrity())

    def test_duplicate_import_rolls_back_all_collections(self):
        record = self.save()
        document = self.store.export()
        document["memories"].append(record)
        fresh = Store(self.path / "import.sqlite")
        with self.assertRaises(Conflict):
            fresh.import_data(document, True)
        self.assertEqual(fresh.projects(), [])

    def test_import_refuses_nonempty_destination(self):
        with self.assertRaises(Conflict):
            self.store.import_data(self.store.export(), True)

    def test_bad_import_cannot_leave_partial_state(self):
        document = self.store.export()
        document["aliases"].append({"alias": "stray", "project": "missing"})
        fresh = Store(self.path / "import.sqlite")
        with self.assertRaises(ValueError):
            fresh.import_data(document, True)
        self.assertEqual(fresh.projects(), [])

    def test_backup_and_cli_restore_preserve_deleted_history_honestly(self):
        record = self.save()
        backup = self.path / "backup.sqlite"
        self.store.backup(backup)
        self.store.forget(record["id"], 1)
        target = self.path / "restored.sqlite"
        result = subprocess.run([sys.executable, "-m", "memory_companion", "--data", str(target), "restore", str(backup)], capture_output=True, text=True, check=True)
        self.assertIn("deleted records may return", result.stdout)
        restored = Store(target)
        self.assertEqual(len(restored.list("reading-desk")), 1)
        self.assertEqual(len(self.store.list("reading-desk")), 0)
        self.assertTrue(restored.integrity())

    def test_backup_cannot_overwrite_live_data_or_existing_file(self):
        with self.assertRaises(ValueError):
            self.store.backup(self.store.path)
        target = self.path / "backup.sqlite"
        self.store.backup(target)
        with self.assertRaises(ValueError):
            self.store.backup(target)


class ModelBoundaryTests(unittest.TestCase):
    def test_invented_citation_flagged_without_rewriting_the_answer(self):
        report = citation_check("An unsupported claim [memory:ID]", {"records": [{"id": "real"}]})
        self.assertFalse(report["id_check_passed"])
        self.assertEqual(report["invalid_ids"], ["ID"])
        valid = citation_check("A claim [memory:real]", {"records": [{"id": "real"}]})
        self.assertTrue(valid["id_check_passed"])
        self.assertIn("factual support still needs review", valid["notice"])
        mixed = citation_check("[Memory: imaginary] and [MEMORY: real ]", {"records": [{"id": "real"}]})
        self.assertEqual(mixed["invalid_ids"], ["imaginary"])

    def test_explicit_cloud_model_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            Model(name="example:cloud")

    def test_only_loopback_endpoints_are_allowed(self):
        for value in ("http://127.0.0.1:8100/v1", "http://localhost:11434", "http://[::1]:11434"):
            self.assertEqual(local_url(value), value)
        for value in ("https://example.com", "http://192.168.1.1", "http://user:pass@localhost", "http://localhost?token=x"):
            with self.assertRaises(ValueError):
                local_url(value)

    def test_missing_model_is_an_error_not_a_fake_reply(self):
        with self.assertRaises(ValueError):
            Model(name="").complete([])

    def test_model_receives_selected_records_not_entire_store(self):
        selection = {"project": "reading-desk", "records": []}
        messages = messages_for("Which GPU?", selection)
        self.assertIn("not recorded", messages[0]["content"])
        self.assertEqual(messages[-1]["content"], "Which GPU?")
        self.assertIn("[]", messages[1]["content"])


class FakeModel:
    def info(self):
        return {"configured": True, "model": "test-double", "backend": "test", "url": "loopback"}

    def complete(self, messages, schema=None):
        self.messages = messages
        return "Test-double response, not model evidence."


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(Path(self.temporary.name) / "web.sqlite")
        self.store.project("reading-desk", "Reading Desk")
        self.model = FakeModel()
        self.server = make_server(self.store, self.model, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.token = self.request("/api/state")["token"]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def request(self, route, payload=None, headers=None):
        defaults = {"X-Companion-Token": getattr(self, "token", "")}
        if payload is not None:
            defaults["Content-Type"] = "application/json"
        request = Request(self.url + route, data=json.dumps(payload).encode() if payload is not None else None,
                          headers={**defaults, **(headers or {})})
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    def test_write_needs_current_token(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/project", {"id": "other", "name": "Other"}, {"X-Companion-Token": "wrong"})
        self.assertEqual(caught.exception.code, 403)
        self.assertEqual(len(self.store.projects()), 1)

    def test_wrong_origin_and_host_are_rejected(self):
        for headers in ({"Origin": "https://untrusted.example"}, {"Host": "untrusted.example"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.assertRaises(HTTPError) as caught:
                self.request("/api/state", headers=headers)
            self.assertEqual(caught.exception.code, 403)

    def test_export_requires_token(self):
        with self.assertRaises(HTTPError):
            self.request("/api/export", headers={"X-Companion-Token": ""})

    def test_chat_memory_toggle_changes_actual_model_input(self):
        self.store.put(scope="project:reading-desk", kind="preference", key="style", content="SYNTHETIC_PREFERENCE", source="test")
        first = self.request("/api/chat", {"project": "reading-desk", "question": "Explain this", "use_memory": True})
        self.assertIn("SYNTHETIC_PREFERENCE", self.model.messages[1]["content"])
        self.assertEqual(len(first["selection"]["records"]), 1)
        second = self.request("/api/chat", {"project": "reading-desk", "question": "Explain this", "use_memory": False})
        self.assertNotIn("SYNTHETIC_PREFERENCE", self.model.messages[1]["content"])
        self.assertEqual(second["selection"]["records"], [])
        self.assertEqual(len(self.store.list("reading-desk")), 1)

    def test_malformed_write_returns_error_without_write(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/save", {"unknown_field": "wrong"})
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(self.store.list("reading-desk"), [])


if __name__ == "__main__":
    unittest.main()
