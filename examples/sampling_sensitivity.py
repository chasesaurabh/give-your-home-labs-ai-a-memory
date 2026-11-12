"""Separate exploratory sampling check; never replaces the baseline study.

Eight selected-memory cases, three declared seeds, card-derived sampling values.
The short answer budget remains800: this is not a reproduction of model-card
benchmarks, long-context settings, or the authors' full recommended recipe.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_companion.model import local_url, NoRedirect

CASES = ["scope-01", "update-01", "progress-01", "temporal-02", "absence-01",
         "paraphrase-03", "injection-02", "handoff-04"]
SEEDS = [17, 43, 101]


def prepare(args):
    if args.output.exists():
        raise ValueError("Choose a new plan filename.")
    original = args.study.read_bytes()
    study = json.loads(original)
    selected = {r["case_id"]: r for r in study["requests"] if r["condition"] == "selected"}
    params = dict(temperature=0.7, top_p=0.8, top_k=20, min_p=0.0,
                  presence_penalty=1.5, repetition_penalty=1.0)
    plan = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                original_sha256=hashlib.sha256(original).hexdigest(),
                design="Exploratory subset selected after baseline review, before sensitivity inference. Not held out or a new aggregate model ranking.",
                cases=CASES, seeds=SEEDS, max_tokens=800, non_thinking=True,
                profiles={"2b": {**params, "temperature": 1.0, "top_p": 1.0, "presence_penalty": 2.0},
                          "9b": params, "27b": params, "122b": params},
                sources={"2b": "https://huggingface.co/Qwen/Qwen3.5-2B",
                         "9b": "https://huggingface.co/Qwen/Qwen3.5-9B",
                         "27b": "https://huggingface.co/Qwen/Qwen3.5-27B",
                         "122b": "https://huggingface.co/Qwen/Qwen3.5-122B-A10B"},
                source_scope="Non-thinking text sampling guidance;122B uses base-model guidance applied to NVIDIA's NVFP4 derivative. Other inference settings held at the short memory-study configuration.",
                requests=[dict(case=selected[case], seed=seed) for seed in SEEDS for case in CASES])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(dict(requests_per_model=len(plan["requests"]), sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))


def run(args):
    raw = args.prepared.read_bytes()
    plan = json.loads(raw)
    args.output.mkdir(parents=True, exist_ok=False)
    state = dict(pid=os.getpid(), started_utc=datetime.now(timezone.utc).isoformat(), status="running",
                 model=args.model, profile=args.profile, completed=0,
                 plan_sha256=hashlib.sha256(raw).hexdigest())
    def save():
        (args.output / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    save()
    opener = build_opener(ProxyHandler({}), NoRedirect())
    url = local_url(args.url)
    with opener.open(url + "/v1/models", timeout=10) as response:
        models = json.load(response)
    if args.model not in [m["id"] for m in models["data"]]:
        raise ValueError("Requested model is not advertised.")
    with (args.output / "responses.jsonl").open("x", encoding="utf-8") as stream:
        for item in plan["requests"]:
            case = item["case"]
            payload = dict(model=args.model, messages=case["messages"], max_tokens=plan["max_tokens"],
                           stream=False, seed=item["seed"], chat_template_kwargs={"enable_thinking": False},
                           **plan["profiles"][args.profile])
            result = dict(case_id=case["case_id"], seed=item["seed"], request=payload,
                          rubric=case["rubric"], selection=case["selection"], semantic_review="pending")
            started = time.perf_counter()
            try:
                request = Request(url + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"})
                with opener.open(request, timeout=180) as response:
                    result["response"] = json.load(response)
                result["status"] = "response_received"
            except HTTPError as error:
                result.update(status="http_error", http_status=error.code, error_body=error.read(10000).decode(errors="replace"))
            except Exception as error:
                result.update(status="request_error", error=str(error))
            result["wall_seconds"] = time.perf_counter() - started
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            state["completed"] += 1
            save()
            print(case["case_id"], item["seed"], result["status"], flush=True)
    state.update(status="complete_unreviewed", finished_utc=datetime.now(timezone.utc).isoformat())
    save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--study", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("run")
    p.add_argument("--prepared", type=Path, required=True)
    p.add_argument("--profile", choices=["2b", "9b", "27b", "122b"], required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args) if args.command == "prepare" else run(args)


if __name__ == "__main__":
    main()
