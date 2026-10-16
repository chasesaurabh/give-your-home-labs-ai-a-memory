"""Optional small-model CPU probe. Requires separately installed torch/transformers.

Downloads only with --download. Later inference is local-files-only, on CPU.
This is a bounded comparison, not the companion's default runtime dependency.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_companion.model import messages_for
from memory_companion.store import Store
from seed_demo import seed

MODEL = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    destination = Path(args.output)
    if destination.exists():
        parser.error("Use a new output file to preserve previous evidence.")
    from huggingface_hub import snapshot_download
    # A plain local directory avoids requiring Windows symlink privileges.
    local_directory = Path(args.cache) / ("qwen3-0.6b-cpu-" + REVISION[:12])
    folder = snapshot_download(MODEL, revision=REVISION, local_dir=local_directory, token=False,
        local_files_only=not args.download,
        allow_patterns=["*.json", "*.safetensors", "tokenizer*", "merges.txt", "vocab.json", "README.md", "LICENSE"])
    # Disable hub access after obtaining the pinned snapshot, before loading inference libraries.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(folder, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(folder, local_files_only=True,
        trust_remote_code=False, torch_dtype=torch.float32).to("cpu").eval()
    report = {"model": MODEL, "revision": REVISION, "device": str(next(model.parameters()).device),
        "torch": torch.__version__, "transformers": transformers.__version__, "threads": 4,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "sampling": {"do_sample": False, "enable_thinking": False, "max_new_tokens": 256},
        "notice": "Small-model probe with greedy non-thinking decoding, not a vendor-recommended general-quality benchmark. No GPU inference or cloud requests.",
        "cases": []}
    destination.parent.mkdir(parents=True, exist_ok=True)
    cases = [
        ("shell", "Which shell should command examples use for Reading Desk?"),
        ("decision", "Where did we decide to keep the Reading Desk database, and why?"),
        ("handoff", "Has restore been verified? What is the next action?"),
        ("no-match", "Which GPU did we buy for this project?"),
        ("procedure", "Which document-service version is recorded? Is its restore step confirmed?")]
    with tempfile.TemporaryDirectory() as temporary:
        store = Store(Path(temporary) / "probe.sqlite")
        seed(store)
        for identifier, question in cases:
            for use_memory in (False, True):
                selected = store.select("reading-desk", question)
                if not use_memory:
                    selected = {**selected, "records": [], "characters": 0}
                messages = messages_for(question, selected)
                prompt = tokenizer.apply_chat_template(messages, tokenize=False,
                    add_generation_prompt=True, enable_thinking=False)
                inputs = tokenizer(prompt, return_tensors="pt")
                start = time.monotonic()
                with torch.inference_mode():
                    generated = model.generate(**inputs, max_new_tokens=256, do_sample=False,
                        pad_token_id=tokenizer.eos_token_id)
                answer = tokenizer.decode(generated[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                record = {"id": identifier, "use_memory": use_memory, "question": question,
                    "selected_records": selected["records"], "answer": answer,
                    "elapsed_seconds": round(time.monotonic()-start, 3), "manual_verdict": "pending"}
                report["cases"].append(record)
                destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                print(identifier, "memory" if use_memory else "baseline", "recorded", flush=True)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["weights_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(folder).glob("*.safetensors")}
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Recorded", len(report["cases"]), "CPU responses.", flush=True)


if __name__ == "__main__":
    main()
