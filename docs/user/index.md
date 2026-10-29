# User Documentation

Welcome to the `cipherbox` user documentation. `cipherbox` is a local-first
CLI secrets manager that stores one JSON file per secret in a local vault
directory.

## Guides

- [Getting Started](getting-started.md) — install, initialize a vault, and run your first commands.
- [Commands](commands.md) — reference for `vault init`, `add`, `show`, `edit`, `delete`, and exit codes.
- [Entry Schema](entry-schema.md) — the versioned entry format and validation rules.
- [Security](security.md) — security status, threat-model limitations, and best practices.
- [Troubleshooting](troubleshooting.md) — common errors and how to resolve them.

## Current status

**Phase 2 (search, filtering, and developer querying) complete.** Plaintext is a
development prototype only — do not migrate real credentials into an
unencrypted vault. Encryption at rest is planned for Phase 3.

## Commands available

`vault init`, `vault add`, `vault show`, `vault edit`, `vault delete`,
`vault list`, `vault search`

Run `vault --help` or `python -m cipherbox --help` for inline help.
