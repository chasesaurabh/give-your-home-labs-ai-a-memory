# Contributing

Keep the core small, local, inspectable, and usable on a single computer. Explain the reader problem before adding a dependency. Prefer a new focused acceptance case over a test that merely repeats implementation details.

Run `py -3.11 -m unittest discover -s tests -v` from the repository root on Windows, or use the compatible Python interpreter selected for your platform. Only directly reproduced platforms should be marked verified.

Use synthetic fixtures. Do not commit user databases, exports, backups, raw private chats, credentials, model weights, or machine-specific paths. Include changes to instructions, examples, and data-format documentation when behavior changes.

Book editions cite frozen tags. New development should not rewrite an existing book release. Document schema compatibility and recovery before any data migration. Changes to inference prompts need new real-model evidence; integration tests with a fake model are not quality evaluations.

Original contributions to this repository follow its MIT license. Third-party materials retain their own licenses and need attribution; the separately published book manuscript and artwork are not part of the code license.
