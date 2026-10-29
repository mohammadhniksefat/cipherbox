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

**Phase 4 (safe writes, recovery, and external modification handling) complete.** Entry files are stored as authenticated AES-GCM envelopes derived from a master password via Argon2id. Writes are atomic; duplicate entry IDs across files are detected as sync conflicts and never silently resolved; backups and restore are available via `vault backup` / `vault restore`. Plaintext Phase 1 vaults remain readable for backward compatibility.

## Commands available

`vault init`, `vault add`, `vault show`, `vault edit`, `vault delete`,
`vault list`, `vault search`, `vault backup`, `vault restore`,
`vault password change`

Run `vault --help` or `python -m cipherbox --help` for inline help.
