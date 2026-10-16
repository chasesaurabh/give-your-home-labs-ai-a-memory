# Setup and recovery

The application requires Python 3.11+ and a local model service. No third-party Python packages are required to run from the source checkout. Memory management, export/import, backup, selection inspection, and the storage labs work without a model. A real model is needed for answers and proposed preferences.

## Start with synthetic data

From the repository root on Windows:

```powershell
py -3.11 examples/seed_demo.py --data data/demo.sqlite
py -3.11 -m memory_companion --data data/demo.sqlite doctor
py -3.11 -m memory_companion --data data/demo.sqlite serve
```

Open `http://127.0.0.1:8765/`. Choose Reading Desk. Inspect selection without a model before attempting chat. Seeding requires a new/empty workspace and does not overwrite an existing one. The `--data` argument is a database filename; using a different one creates a separate workspace.

## Configure a downloaded local model

For an already installed Ollama service with a downloaded local model, set `MEMORY_MODEL` to the exact local model identifier. The default backend is `ollama`, at `http://127.0.0.1:11434`. Configure Ollama's server-side cloud-disable option using its official documentation. Never select a cloud model for this book's local path.

For a local compatible inference service, set these before launching; replace the port and model with the ones your actual local server exposes:

```powershell
$env:MEMORY_BACKEND = 'compatible'
$env:MEMORY_MODEL_URL = 'http://127.0.0.1:8100/v1'
$env:MEMORY_MODEL = 'nemotron-super-120b-fp4'
py -3.11 -m memory_companion --data data/demo.sqlite serve
```

The displayed model/port above identify the directly tested development server. They do not install that server or establish a reader's required model size. Model server setup and model licensing are separate from this application. No cloud API key or paid inference service is required. Check [local-only behavior](local-only.md) and the [version matrix](version-matrix.md) for the exact evidence boundary.

## Read, save, correct, and forget

Select a project and use the memory panel. New keys start at revision 0 before first save. Edit existing records through their Edit button so the expected revision is included. A stale edit returns a conflict; reload, inspect, and make a deliberate new edit rather than blindly retrying.

Each question starts without prior chat history and includes only the selected memory. Displayed answers remain visible until cleared, but are not fed into later questions. The memory toggle changes supplied context without deleting records. Inspect selection shows the request data without making an inference call.

## Export, backup, and restore

Export and backup destinations must be new files:

```powershell
py -3.11 -m memory_companion --data data/demo.sqlite export exports/demo.json
py -3.11 -m memory_companion --data data/demo.sqlite backup backups/demo.sqlite
py -3.11 -m memory_companion --data data/restored.sqlite restore backups/demo.sqlite
py -3.11 -m memory_companion --data data/restored.sqlite doctor
```

Restore refuses an existing destination and verifies database integrity/version/relationships. Rehearse in a separate workspace, then inspect restored records; an old backup can restore records you forgot later. Do not replace a live database while a server is using it. The Backup button creates a unique backup inside the current database directory's `backups` folder.

Readable import also requires an empty destination:

```powershell
py -3.11 -m memory_companion --data data/imported.sqlite import exports/demo.json
py -3.11 -m memory_companion --data data/imported.sqlite import exports/demo.json --apply
```

The first command validates and previews without applying. The second applies in one transaction and preserves IDs, revisions, and timestamps. Existing nonempty workspaces are never silently merged. Blank worksheets are not valid import files.

## Troubleshooting

- No model configured: set the exact local model identifier before starting the process. Storage features still work.
- Model unavailable: confirm its local service and model name; a timeout does not mean a memory write occurred.
- Invalid proposal: no memory is saved; inspect the statement or use explicit manual save.
- Unknown project: use a listed stable identifier, or create a project before saving scoped records.
- Port in use: choose another loopback port with `serve --port 8766`, then open that exact address.
- Import conflict: use a new destination data file, not the workspace that already contains projects.
- Unsupported database version: open it with a compatible companion release; do not edit version markers to bypass checks.
- Forgotten fact still appears: inspect current selection, old displayed answers, exports, and restored backups separately.

Ctrl+C stops the server. No access log or automatic background memory capture is maintained. See SECURITY.md for the single-user boundary and deletion limits.
