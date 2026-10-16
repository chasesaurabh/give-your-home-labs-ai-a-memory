"""Record matched real local-model cases. This is an evidence collector, not a universal quality score."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_companion.model import Model, messages_for, suggest
from memory_companion.store import Store
from seed_demo import seed


CASES = [
    ("shell", "Which command shell should examples use for this project?", ["PowerShell"], "Should follow the selected shell preference; no-memory baseline should acknowledge missing preference."),
    ("decision", "Where did we decide to keep the Reading Desk database, and why?", ["mini PC"], "Must retain the actual location and reason; no invented completed migration."),
    ("rename", "Is Shelf a second unfinished project, or what happened to it?", ["Reading Desk"], "Must recognize the earlier name and avoid counting a second project."),
    ("handoff", "Where did we leave off? Has restore been tested?", ["restore"], "Must preserve untested restore and next action rather than inventing completion."),
    ("incident", "What happened in the wrong-port incident and which attempt did not work?", ["8765"], "Must preserve failed browser restart and successful port correction."),
    ("near-match", "A connection is failing again. Is the old port fix proven to work now?", [], "Must not diagnose the new event from historical similarity alone."),
    ("procedure", "For document-service, which version is saved and is the restore step confirmed?", ["2"], "Must preserve version 2 and attempted, unconfirmed restore."),
    ("no-match", "Which GPU did we buy for this project?", [], "Must state the purchase is not recorded; no invented hardware."),
    ("override", "For this reply only, use Bash instead of my saved shell preference. Show a command to print hello.", ["hello"], "Should follow the current request without editing the saved PowerShell preference."),
    ("held-out-handoff", "I'm back after a break. What still needs proving before I can trust recovery?", ["restore"], "Held-out phrasing: keep recovery verification outstanding.")
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    model = Model()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        parser.error("Choose a new evidence output path; do not overwrite an earlier run.")
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "model": model.info(),
              "sampling": {"temperature": 0, "max_output_tokens": 1600 if model.backend == "compatible" else 1200},
              "fixture": "examples/seed_demo.py", "fixture_sha256": hashlib.sha256(Path(__file__).with_name("seed_demo.py").read_bytes()).hexdigest(),
              "notice": "All content is synthetic. Review factual support manually. Keyword checks alone do not establish a pass.", "cases": []}
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "eval.sqlite")
        seed(store)
        for identifier, question, hints, rubric in CASES:
            for use_memory in (False, True):
                selection = store.select("reading-desk", question)
                if not use_memory:
                    selection = {**selection, "records": [], "characters": 0}
                messages = messages_for(question, selection)
                start = time.monotonic()
                record = {"id": identifier, "use_memory": use_memory, "question": question,
                          "rubric": rubric, "request_messages": messages, "selection": selection}
                try:
                    record["answer"] = model.complete(messages)
                    record["hint_matches"] = {hint: hint.lower() in record["answer"].lower() for hint in hints}
                    record["manual_verdict"] = "pending"
                except ValueError as error:
                    record["error"] = str(error)
                    record["manual_verdict"] = "request_failed"
                record["elapsed_seconds"] = round(time.monotonic() - start, 3)
                report["cases"].append(record)
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                print(identifier, "memory" if use_memory else "baseline", record["manual_verdict"], flush=True)
        report["proposals"] = []
        for statement in ("For this project I prefer numbered steps.", "The fictional book cover has a green chair."):
            before = store.export()
            try:
                result = suggest(model, store, "reading-desk", statement)
                report["proposals"].append({"statement": statement, "result": result,
                    "memories_unchanged": store.export()["memories"] == before["memories"], "manual_verdict": "pending"})
            except ValueError as error:
                report["proposals"].append({"statement": statement, "error": str(error), "manual_verdict": "request_failed"})
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Recorded", len(report["cases"]), "paired-case responses and", len(report["proposals"]), "proposal attempts.", flush=True)


if __name__ == "__main__":
    main()
