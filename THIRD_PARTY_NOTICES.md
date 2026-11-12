# Third-party notices

Original companion source, synthetic fixtures, worksheets, and documentation: MIT, copyright 2026 Saurabh Chase. Application screenshots show this original UI and synthetic data.

Runtime code imports only Python's standard library. Python and its bundled SQLite are installed separately under their respective licenses. Build tooling uses setuptools when packaging; no build dependency is required to run directly from this checkout. No third-party JavaScript, CSS framework, external fonts, or analytics are bundled.

Inference runtimes and model weights are not redistributed. Their download, use, and any output conditions depend on their own licenses. Choose and review a model license independently of this repository's MIT license. Names of third-party projects identify compatibility or testing; no affiliation is implied.

The model lock and synthetic research bundle identify the exact tested configurations. Qwen's 2B/9B/27B checkpoints and NVIDIA's Qwen3.5-122B-A10B-NVFP4 card identify Apache 2.0 licensing. No model weights or runtime image layers are included here. Consult the licenses shipped with a download and the official cards before use:

- https://huggingface.co/Qwen/Qwen3.5-2B
- https://huggingface.co/Qwen/Qwen3.5-9B
- https://huggingface.co/Qwen/Qwen3.5-27B
- https://huggingface.co/nvidia/Qwen3.5-122B-A10B-NVFP4

The research bundle contains original synthetic prompts, their actual generated responses and separately labeled AI-assisted case annotations. It does not redistribute third-party evaluation datasets or claim vendor benchmark results. No particular large checkpoint is necessary for running the storage/UI companion, and equal behavior across models is not promised.
