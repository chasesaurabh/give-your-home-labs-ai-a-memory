"""Run the optional bounded local recall agent against synthetic demo data."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_companion.agent import run_agent
from memory_companion.model import Model
from memory_companion.store import Store
from seed_demo import seed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        parser.error("Choose a new evidence file.")
    try:
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "agent.sqlite")
            seed(store)
            before = store.export()["memories"]
            model = Model()
            result = run_agent(model, store, "reading-desk", args.question)
            result.update(model=model.info(), recorded_at=datetime.now(timezone.utc).isoformat(),
                          memories_unchanged=store.export()["memories"] == before,
                          notice="Actual local inference with a read-only scoped recall tool; no general autonomy claim.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"turns": result["turns"], "tool_calls": len(result["trace"]),
                          "memories_unchanged": result["memories_unchanged"]}))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + "\n")
