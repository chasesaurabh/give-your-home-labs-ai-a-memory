# Version and verification matrix

Development evidence, October 16, 2026. A final book release will freeze exact code and repeat the relevant checks. This table is not a guarantee about untested platforms or models.

| Component | Observed version or identity | Evidence |
|---|---|---|
| Python | 3.11.9 | Direct storage, CLI, HTTP, backup/restore test runs |
| SQLite | 3.45.1 through Python | Direct store and recovery checks |
| Operating system | Windows, build 26300 | Direct application and CLI work |
| Compatible local inference | vLLM 0.30.0 | Existing running local container; actual inference |
| Model | NVIDIA Nemotron 3 Super 120B-A12B NVFP4 | Local model-list identity; matched synthetic response cases |
| Ollama-native adapter | Implemented; real-engine test pending | Do not label integration verified until actually reproduced |
| macOS/Linux | Not yet directly reproduced | Python portability is not equivalent to an OS test |
| Browser | Codex in-app Chromium browser | Actual page rendering and local-model handoff interaction |

The large development checkpoint is not a minimum hardware recommendation. The companion's storage/UI code has no GPU dependency; inference capacity and response reliability depend on the selected local runtime and model. No speed or accuracy advantage over hosted models is claimed.
