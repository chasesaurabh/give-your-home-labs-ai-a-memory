"""Eighteen reproducible chapter checkpoints using disposable synthetic data.

These exercises prove storage/application mechanisms, not actual model answers.
Use evaluate_local.py separately for recorded inference.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_companion.model import messages_for
from memory_companion.store import Store, Conflict
from seed_demo import seed


TITLES = ["Memory and context", "Workspace health", "A persisted preference", "A sourced record",
          "Project separation", "Inspectable records", "Reviewed proposal", "A recorded decision",
          "A reviewed handoff", "Restart and alias", "Bounded retrieval", "Revision conflict",
          "Forgetting and expiry", "Portable recovery", "An evidence scorecard", "Incident comparison",
          "Procedure progress", "Upgrade rehearsal"]


def exercise(chapter, directory):
    store = Store(directory / "lab.sqlite")
    seed(store)
    report = {"chapter": chapter, "title": TITLES[chapter-1], "model_called": False}
    rows = store.list("reading-desk")
    pref = next(row for row in rows if row["key"] == "shell")
    if chapter == 1:
        report["kinds"] = sorted({row["kind"] for row in rows})
        report["lesson"] = "The saved store and a current request are separate objects."
    elif chapter == 2:
        assert store.integrity()
        report.update(integrity=True, projects=len(store.projects()))
    elif chapter == 3:
        result = subprocess.run([sys.executable, "-m", "memory_companion", "--data", str(store.path),
                                 "list", "reading-desk"], capture_output=True, text=True, check=True,
                                 cwd=Path(__file__).resolve().parents[1])
        assert pref["id"] in {row["id"] for row in json.loads(result.stdout)}
        report["persisted_record"] = pref
    elif chapter == 4:
        assert pref["source"] and pref["scope"] and pref["revision"] == 1
        report["inspect"] = pref
    elif chapter == 5:
        selected = store.select("lab-journal", "Which shell?")
        assert all(row["scope"] in {"global", "project:lab-journal"} for row in selected["records"])
        assert "PowerShell" not in json.dumps(selected)
        report["selection"] = selected
    elif chapter == 6:
        report["export_preview"] = {"format": store.export()["format"], "record_count": len(store.export()["memories"])}
        report["next"] = "Use the real UI to inspect, edit, and forget a synthetic record."
    elif chapter == 7:
        fields = dict(scope="project:reading-desk", kind="preference", key="lab-format", content="Use numbered steps", source="Synthetic explicit review exercise")
        proposal = store.propose(fields)
        assert not any(row["key"] == "lab-format" for row in store.list("reading-desk"))
        store.review(proposal["id"], False)
        proposal = store.propose(fields)
        store.review(proposal["id"], True)
        report["saved_after_explicit_review"] = True
        report["notice"] = "Proposal fields were supplied by this deterministic lab, not extracted by a model."
    elif chapter == 8:
        report["decision"] = next(row for row in rows if row["key"] == "database-location")
        assert report["decision"]["metadata"]["state"] == "approved"
    elif chapter == 9:
        handoff = next(row for row in rows if row["kind"] == "handoff")
        assert handoff["metadata"]["reviewed"]
        assert "outcome is not verified" in handoff["content"]
        report["reviewed_handoff"] = handoff
    elif chapter == 10:
        reopened = Store(store.path)
        assert reopened.resolve("shelf") == "reading-desk"
        report["one_project_identity"] = reopened.resolve("shelf")
        report["retrieved_records"] = len(reopened.list("shelf"))
    elif chapter == 11:
        selected = store.select("reading-desk", "wrong port", budget=3500)
        assert selected["characters"] <= selected["budget"]
        report["selection"] = selected
    elif chapter == 12:
        fields = {key: pref[key] for key in ("scope", "kind", "key", "content", "source", "metadata", "expires_at")}
        fields["content"] = "Use Bash for this revised project preference."
        updated = store.put(**fields, expected_revision=1)
        try:
            store.put(**fields, expected_revision=1)
            raise AssertionError("Stale write was accepted")
        except Conflict:
            pass
        report.update(current_revision=updated["revision"], stale_edit_rejected=True)
    elif chapter == 13:
        store.forget(pref["id"], 1)
        expiry = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        store.put(scope="project:reading-desk", kind="preference", key="temporary", content="Expired synthetic fact", source="lab", expires_at=expiry)
        selected = store.select("reading-desk", "shell temporary")
        assert pref["id"] not in {row["id"] for row in selected["records"]}
        assert not any(row["key"] == "temporary" for row in selected["records"])
        report.update(forgotten_excluded=True, expired_excluded=True)
    elif chapter == 14:
        store.backup(directory / "backup.sqlite")
        target = Store(directory / "imported.sqlite")
        document = store.export()
        target.import_data(document)
        assert target.projects() == []
        target.import_data(document, True)
        assert target.export()["memories"] == document["memories"]
        report.update(preview_unchanged=True, round_trip_preserved=True, integrity=target.integrity())
    elif chapter == 15:
        selected = store.select("reading-desk", "Which shell?")
        messages = messages_for("Which shell?", selected)
        report["scorecard"] = {"store_integrity": store.integrity(), "selected_records": len(selected["records"]),
                               "request_messages": len(messages), "model_quality": "not evaluated by this lab"}
    elif chapter == 16:
        incidents = [row for row in rows if row["kind"] == "incident"]
        assert len(incidents) == 2
        wrong_port = next(row for row in incidents if row["key"] == "wrong-port")
        assert wrong_port["metadata"]["attempts"][0]["outcome"] == "No change"
        report["contrasting_incidents"] = incidents
    elif chapter == 17:
        procedure = next(row for row in rows if row["kind"] == "procedure")
        result = store.step(procedure["id"], 2, "attempted", "Synthetic reader began writing recovery notes", 1)
        assert result["metadata"]["steps"][2]["state"] == "attempted"
        assert result["metadata"]["steps"][1]["state"] == "attempted"
        report["procedure"] = result
        report["command_executed"] = False
    else:
        backup = directory / "before-upgrade.sqlite"
        store.backup(backup)
        rehearsal = directory / "rehearsal.sqlite"
        subprocess.run([sys.executable, "-m", "memory_companion", "--data", str(rehearsal), "restore", str(backup)],
                       capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parents[1])
        assert Store(rehearsal).integrity()
        assert store.export()["memories"] == Store(rehearsal).export()["memories"]
        report.update(rehearsal_integrity=True, original_unchanged=True)
    report["checkpoint"] = "passed_for_stated_deterministic_scope"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter", type=int, choices=range(1, 19), nargs="?")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not args.all and args.chapter is None:
        parser.error("Choose a chapter number or --all")
    results = []
    for chapter in range(1, 19) if args.all else [args.chapter]:
        with tempfile.TemporaryDirectory() as directory:
            results.append(exercise(chapter, Path(directory)))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
