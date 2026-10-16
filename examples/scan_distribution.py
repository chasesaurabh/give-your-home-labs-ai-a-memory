"""Small tracked-file hygiene check. Not a substitute for reviewing the distribution."""
from pathlib import Path
import re
import subprocess

files = subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0")
patterns = [r"sk-[A-Za-z0-9_-]{24,}", r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"]
forbidden, suspected = [], []
checked = 0
for name in filter(None, files):
    path = Path(name)
    if any(part in {"data", "backups", "exports", ".env", "models"} for part in path.parts) or path.suffix.lower() in {".sqlite", ".db", ".gguf", ".safetensors"}:
        forbidden.append(name)
    if path.suffix.lower() in {".py", ".md", ".json", ".toml", ".js", ".html", ".css"}:
        checked += 1
        content = path.read_text(encoding="utf-8")
        if any(re.search(pattern, content) for pattern in patterns):
            suspected.append(name)
print({"text_files_checked": checked, "suspected_secret_files": suspected, "forbidden_files": forbidden})
raise SystemExit(bool(forbidden or suspected))
