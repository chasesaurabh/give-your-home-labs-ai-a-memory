# Inspect and reproduce the local memory study

This directory contains original fictional memory tasks and actual local-model responses collected on November 12, 2026. It lets you inspect failures, recalculate the reported measurements and repeat the same requests on your own local model. It contains no book manuscript, production checklist, user memories or model weights.

## What the files mean

| File or directory | Contents |
|---|---|
| `prepared.json` | Frozen 32 questions, rubrics, selected records and 96 request messages |
| `baseline/` | Four complete 96-response runs, including every original model answer |
| `sensitivity-prepared.json` | Eight selected-memory cases, three declared seeds and sampling parameters |
| `sensitivity/` | All 24 responses per profile; no best-seed replacement |
| `workflows/` | Actual 9B/122B extraction and scoped-recall traces, 18 cases each |
| `case-annotations.json` | AI-assisted manual observations and requested-fact recovery labels |
| `sensitivity-annotations.json` | Observations for every sensitivity case and seed |
| `SHA256.json` | Byte lengths and hashes of the evidence payloads |

`semantic_review: pending` inside the original collector rows describes their state when collected. The separate annotation files were added after reading the responses; original rows were not rewritten. A hash checks agreement with this manifest, not the trustworthiness of its author.

From the repository root, recalculate coverage, median complete-request times, citation-ID membership and the separately labeled manual fact-recovery counts:

```powershell
py -3.11 examples/summarize_study.py
```

This needs no GPU, model download or third-party Python package. Read the actual response and supporting record before accepting an annotation. ID membership is not factual support. Requested-fact recovery is not whole-answer correctness, attack resistance or a general accuracy estimate.

## Recorded configuration

The host ran Windows with an NVIDIA RTX PRO 6000 Blackwell Workstation Edition. The device reported 97,887 MiB and driver 582.16. The application used Python 3.11.9/SQLite 3.45.1; the pinned container reported vLLM 0.30.0, Python 3.12.3 and PyTorch 2.13.0+cu130. Full model revisions, artifact hashes and the Docker image digest are in [the model lock](../../configs/model-artifacts.lock.json).

| Profile | Repository | Engine allocation fraction |
|---|---|---:|
| 2B | Qwen/Qwen3.5-2B | 0.09 |
| 9B | Qwen/Qwen3.5-9B | 0.22 |
| 27B | Qwen/Qwen3.5-27B | 0.68 |
| 122B | nvidia/Qwen3.5-122B-A10B-NVFP4 | 0.88 |

The first three used dense BF16 weights. The 122B mixture-of-experts configuration used ModelOpt FP4 weights and FP8 KV cache. All used eager execution, a 4,096-token context, one simultaneous sequence, non-thinking generation and no image/video inputs. Main requests used temperature 0 and an 800-token output cap. Requests ran sequentially; no first request was removed as warm-up. The fractions are allocation settings on this machine, not minimum-GPU recommendations. Architecture, quantization and cache precision confound a pure parameter-count comparison.

Sensitivity uses Qwen model-card non-thinking text sampling values: 2B temperature 1/top-p 1/presence-penalty 2; other profiles temperature 0.7/top-p 0.8/presence-penalty 1.5; all top-k 20/min-p 0/repetition-penalty 1. Seeds 17, 43 and 101 are retained. The short response/context settings remain. The 122B derivative uses base-Qwen guidance. This does not reproduce vendor long-output benchmarks.

## Repeat the frozen requests

Follow [model setup](../../docs/setup.md) and the downloader/launcher help to acquire and start one locked profile. Keep the engine's advertised alias consistent with the chosen profile. For a running `memory-2b` server on loopback 18106:

```powershell
py -3.11 examples/memory_study.py run `
  --prepared experiments/memory-study-2026-11-12/prepared.json `
  --url http://127.0.0.1:18106 --model memory-2b `
  --output data/study/repeat-2b-01
py -3.11 examples/sampling_sensitivity.py run `
  --prepared experiments/memory-study-2026-11-12/sensitivity-prepared.json `
  --profile 2b --url http://127.0.0.1:18106 --model memory-2b `
  --output data/sensitivity/repeat-2b-01
```

Use a new output directory for each attempt. The collectors refuse to overwrite an existing run. Start another profile only after finishing and stopping the current one; preserve failed requests as well as successful responses. Your timing and text can differ even with the same settings. No extra inference should run concurrently during a timing comparison.

## Interpret the failures

There are 32 questions in eight related categories, each asked with no memory, actual selection and evaluator-supplied supporting evidence. The latter is an oracle control, not an app feature. The selector supplied all required records in 26 of 28 fact-bearing cases; four absent-fact cases are excluded. Two paraphrases failed before generation.

One frozen criterion equates “zipped journals” with “compressed logs” without explicitly establishing equivalence. Cautious refusal is defensible. Another prohibits literal attack tokens, so quoting a token to reject it can fail that rule without obeying the attack. Both ambiguities remain visible; neither was removed to improve a score.

Larger configurations often recovered the requested facts while adding unsupported claims, such as saying an underlying issue was resolved from two dated test observations. The 2B configuration also exhibited wrong dates, fabricated IDs and acceptance of a hostile checksum instruction. Sensitivity changed some failures rather than removing them. The workflow traces expose different issues: preference keys can duplicate an existing meaning, and a valid tool call can still produce an incorrect progress summary.

These are related synthetic cases, reviewed with AI assistance rather than independent human annotation. They are application diagnostics, not a held-out benchmark, a model leaderboard or a security guarantee. The sensitivity subset was selected after baseline reading. No confidence interval or universal winner is inferred.

Original fixtures, evaluation code and annotations are covered by this repository's MIT license. Outputs are identified as generated responses from the named models; model/runtimes retain their own licenses. See [third-party notices](../../THIRD_PARTY_NOTICES.md).
