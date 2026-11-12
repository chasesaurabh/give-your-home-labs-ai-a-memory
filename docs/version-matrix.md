# Version and verification matrix

Current application-study evidence was collected on November 12, 2026. Historical native/CPU checks are labeled separately below. This matrix states what was observed, not a guarantee about other platforms or models.

| November 12 component | Observed version or identity | Evidence and limit |
|---|---|---|
| Host application | Python 3.11.9; SQLite 3.45.1; Windows | Storage, CLI, HTTP, actual browser interaction and isolated installed-package checks |
| GPU | RTX PRO 6000 Blackwell Workstation Edition; 97,887 MiB; driver 582.16 | Actual device report; not a minimum reader requirement |
| Container | Pinned vLLM 0.30.0 image; Python 3.12.3; PyTorch 2.13.0+cu130 | Runtime reports and real completions |
| Dense checkpoints | Qwen3.5 2B, 9B, 27B, BF16 weights | 96 main and 24 sensitivity responses per profile |
| Quantized checkpoint | NVIDIA Qwen3.5-122B-A10B-NVFP4, FP8 KV cache | 96 main and 24 sensitivity responses; different architecture/precision confound size comparisons |
| Extraction and recall agent | 9B and 122B | 12 extraction and 6 actual recall cases each; semantic failures retained |
| First model acquisition | Locked 2B files, 4,571,272,453 bytes | Actual fresh download, hash verification, public launcher and READY completion |
| Installed application | Isolated wheel installation; bundled web assets | Actual with/without-memory HTTP inference, including a failed no-memory answer |
| Recovery | Browser JSON import and CLI SQLite restore to new destinations | All fields of 11 fictional memories, 2 projects and 1 alias preserved |
| First-edition data | Export/database produced by preserved book-v1.0.0 code | Nine fictional memories preserved by import and by direct opening; not every historical user database |

The [model lock](../configs/model-artifacts.lock.json) records full revisions and content hashes. The [retained study](../experiments/memory-study-2026-11-12/README.md) includes prompts, outputs, sampling settings, raw timing and limitations. None of the model rows means that every answer was correct. Tests with a model double remain separate from these real-model cases.

## Historical integration evidence

The following checks were recorded on October 16, 2026. They do not replace the newer four-model comparison.

| Component | Observed version or identity | Evidence |
|---|---|---|
| Python | 3.11.9 | Direct storage, CLI, HTTP, backup/restore test runs |
| SQLite | 3.45.1 through Python | Direct store and recovery checks |
| Operating system | Windows, build 26300 | Direct application and CLI work |
| Compatible local inference | vLLM 0.30.0 | Existing running local container; actual inference |
| Model | NVIDIA Nemotron 3 Super 120B-A12B NVFP4 | Local model-list identity; matched synthetic response cases |
| Ollama-native adapter | Ollama 0.40.5 portable Windows, qwen3:0.6b Q4_K_M | Two actual CPU-only shell responses; invalid-key proposal rejected; no general quality pass |
| macOS/Linux | Not yet directly reproduced | Python portability is not equivalent to an OS test |
| Browser | Codex in-app Chromium browser | Actual page rendering and local-model handoff interaction |
| Optional CPU model | Qwen3-0.6B, revision c1899de289a04d12100db370d81485cdf75e47ca | Ten actual CPU responses; semantic failures retained |
| Optional CPU libraries | torch 2.12.0.dev20260329+cu128; transformers 4.51.0 | Local-files-only CPU loading, no remote model code |
| Optional bounded agent | Compatible local Nemotron service above | Actual scoped recall tool call; state unchanged; semantic limitations retained |

The large development checkpoint is not a minimum hardware recommendation. The companion's storage/UI code has no GPU dependency; inference capacity and response reliability depend on the selected local runtime and model. No speed or accuracy advantage over hosted models is claimed.

The native checkpoint digest was `7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435`. The isolated native engine reported zero VRAM for that loaded model and cloud features disabled. Its no-memory response fabricated a citation placeholder, and the with-memory answer recovered PowerShell without the requested supporting ID. This is direct integration evidence with semantic limitations.
