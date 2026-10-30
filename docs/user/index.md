# User Documentation

Welcome to the `cipherbox` user documentation. `cipherbox` is a local-first
CLI secrets manager that stores one JSON file per secret in a local vault
directory.

## Guides

- [Getting Started](getting-started.md) — install, initialize a vault, and run your first commands.
- [Commands](commands.md) — reference for all `vault` commands and exit codes.
- [Entry Schema](entry-schema.md) — the versioned entry format and validation rules.
- [Security](security.md) — security status, threat-model limitations, and best practices.
- [Troubleshooting](troubleshooting.md) — common errors and how to resolve them.

## Current status

**Phase 6 (developer productivity features) complete.** Entry files are stored as authenticated AES-GCM envelopes derived from a master password via Argon2id. Writes are atomic; duplicate entry IDs across files are detected as sync conflicts and never silently resolved; backups and restore are available via `vault backup` / `vault restore`. Import/export and encrypted backup/restore are available via `vault export` / `vault import` / `vault env export`. Plaintext Phase 1 vaults remain readable for backward compatibility.

## Commands available

`vault init`, `vault add`, `vault show`, `vault edit`, `vault delete`,
`vault list`, `vault search`, `vault get`, `vault env export`,
`vault env list`, `vault generate password`, `vault check`, `vault doctor`,
`vault copy`, `vault backup`, `vault restore`, `vault password change`,
`vault export`, `vault import`

Run `vault --help` or `python -m cipherbox --help` for inline help.
