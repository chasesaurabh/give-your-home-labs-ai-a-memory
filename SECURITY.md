# Security and data boundaries

This is a single-user educational companion intended for the same computer as its browser and inference engine. It is not a public or multi-user web service. Do not expose its port through a tunnel, router, reverse proxy, or LAN binding.

The app binds to 127.0.0.1, checks the Host and Origin headers, rejects cross-site requests, requires a per-process request token for writes/exports, limits request sizes, and renders model/memory text as text rather than HTML. These reduce specific browser and application risks; they do not protect against another process or account already able to read the database on your computer.

Memory scope is a project-selection boundary within one user's workspace, not authentication or access control between people. Recalled content never authorizes shell commands or expands access. Model proposals require exact user review and revision checks. The current chat path has no execution or memory-write tools.

Logical forgetting removes the row from future lookup, clears pending proposal copies, and records a content-free audit event. Existing answers, earlier exports/backups, filesystem snapshots, and storage hardware may retain information. SQLite secure_delete is enabled for live operations, but the app makes no universal physical-erasure guarantee.

Do not send private user memories in public issues. Reproduce problems with synthetic records. Report security concerns using GitHub's private vulnerability reporting if enabled; otherwise open a minimal issue asking for a private reporting channel without exploit payloads or private data. No private contact address is published here.
