# Version and verification matrix

Development evidence, October 16, 2026. A final book release will freeze exact code and repeat the relevant checks. This table is not a guarantee about untested platforms or models.

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
