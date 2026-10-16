# Local inference and memory

The companion keeps memory in a local SQLite database. Browser assets are bundled: no CDN, external font, analytics script, web search, cloud memory service, API-key field, or cloud fallback is included. The browser talks to the loopback application; Python talks to the configured loopback inference service.

The model adapter accepts only HTTP loopback addresses, disables environment proxies, refuses redirects, and rejects explicit `:cloud` model identifiers. Those checks limit the companion's own network destination. They cannot prove what an arbitrary service listening on localhost does upstream. Connect an actual local inference engine with downloaded weights, not a local proxy to a hosted API.

For Ollama, use downloaded local models. Its official FAQ documents `OLLAMA_NO_CLOUD=1` / the disable-cloud setting; apply the documented server-side control and restart Ollama as required. Installing the companion does not reconfigure an existing inference server. See [Ollama FAQ](https://docs.ollama.com/faq). Downloading models and installing software initially require access to their sources; this is separate from inference after setup.

Development verification used a resident NVIDIA Nemotron 3 Super 120B-A12B NVFP4 checkpoint served by local vLLM 0.30.0 on loopback. Twenty responses and two extraction attempts were recorded using synthetic data. This identifies an actual local test, not a minimum reader hardware requirement or proof about all smaller models. The same companion includes an Ollama-native adapter; its real-engine verification is tracked separately from the compatible endpoint.

To evaluate local operation, inspect the served model identity, keep the engine itself local, and repeat a bounded inference test without internet access after setup. A loopback URL alone and a successful database test are insufficient evidence for end-to-end offline claims. Backups, exports, and screenshots remain files under your control; store real memory data privately.
