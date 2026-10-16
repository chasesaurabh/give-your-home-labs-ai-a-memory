"""Seed original fictional data into an empty companion workspace."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_companion.store import Store


def seed(store):
    if store.projects() or store.export()["memories"]:
        raise ValueError("Use an empty database for the synthetic demo.")
    store.project("reading-desk", "Reading Desk", ["shelf"])
    store.project("lab-journal", "Lab Journal")
    records = [
        ("preference", "shell", "Use PowerShell examples for this project.", {}),
        ("preference", "answer-style", "Prefer concise explanations, with steps when useful.", {}),
        ("decision", "project-name", "Shelf was the earlier name of Reading Desk. They are one project; Shelf is historical reference, not another outstanding project.", {"state": "confirmed", "evidence": "Synthetic owner decision"}),
        ("decision", "database-location", "Keep the Reading Desk database on the mini PC, not the NAS. The reason is simpler local recovery.", {"state": "approved", "conditions": ["Single-user local application"]}),
        ("handoff", "latest-session", "Export was verified. A synthetic restore rehearsal was started, but its successful outcome is not verified. Next action: complete and verify the restore rehearsal in a separate disposable data directory.", {"completed": ["Export"], "attempted": ["Restore rehearsal started; outcome unconfirmed"], "next_action": "Complete and verify restore rehearsal", "reviewed": True}),
        ("incident", "wrong-port", "A synthetic Reading Desk connection failed on port 8766. The app was listening on 8765. Correcting the address restored access.", {"environment": "Synthetic demo", "attempts": [{"action": "Restart browser", "outcome": "No change"}, {"action": "Correct port to 8765", "outcome": "Access restored"}]}),
        ("incident", "stopped-service", "A synthetic connection failed because the companion process was stopped. Starting the process restored access on the unchanged port 8765.", {"environment": "Different synthetic incident", "attempts": [{"action": "Start stopped process", "outcome": "Access restored"}]}),
        ("procedure", "document-service", "Approved routine for documenting a local service. Recall does not execute commands or confirm completed work.", {"version": 2, "steps": [
            {"instruction": "Record the service purpose", "state": "confirmed", "evidence": "Synthetic owner confirmed the purpose note exists"},
            {"instruction": "Verify restore in a disposable workspace", "state": "attempted", "evidence": "Synthetic rehearsal started, outcome not confirmed"},
            {"instruction": "Write the recovery instructions", "state": "pending", "evidence": ""}]})
    ]
    for kind, key, content, metadata in records:
        store.put(scope="project:reading-desk", kind=kind, key=key, content=content,
                  metadata=metadata, source="Original synthetic book demonstration, 2026-10-16")
    store.put(scope="project:lab-journal", kind="preference", key="shell", content="Use Bash examples in Lab Journal.", source="Original synthetic comparison")
    return len(records) + 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/demo.sqlite")
    args = parser.parse_args()
    try:
        count = seed(Store(args.data))
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
    print(f"Created {count} synthetic memories across two projects. No model was called.")
