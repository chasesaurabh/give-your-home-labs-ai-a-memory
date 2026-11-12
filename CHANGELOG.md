# Companion changes

## 0.2.0

- Captures preference identity and revision before model inference, and rejects a suggestion if the record changes while the model is responding.
- Exports projects, aliases and memories from one consistent SQLite read transaction.
- Adds structured JSON editing for handoffs, incidents and decisions. Procedure progress keeps its dedicated controls.
- Clears stale cards when switching projects and limits pending proposals to the selected project and global scope, including earlier-name aliases.
- Adds hash-verified model acquisition, a pinned loopback-only GPU launcher and complete synthetic model-study collectors.
- Includes original study requests, all retained model responses, separate case annotations and a calculation script. These diagnostics include semantic failures; they do not certify model accuracy.
- Adds a complete portable import fixture and an ordinary reader-facing chapter guide.

The `homelab-memory-v1` transfer format remains unchanged. A synthetic database and export produced by the preserved first-edition code were checked with this application path. Retain a backup and rehearse an upgrade on a separate copy of your own data; that compatibility observation is not a guarantee about every historical database.

## 0.1.0

The first-edition release remains available as `book-v1.0.0`, with its original commit and documentation. Its code and reference links have not been rewritten.
