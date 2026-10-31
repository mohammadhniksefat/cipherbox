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
- [Operating systems and filesystems](os-filesystems.md) — supported platforms and filesystem guidance.
- [Release builds and installation](../release.md) — install from PyPI or source, reproducible release builds, shell completion.

## Current status

**Phase 7 (release hardening and documentation) complete.** Stable MVP release:
installable via PyPI or source, reproducible release builds, shell completion
(`vault completion bash|zsh|powershell`), documented supported operating systems
and filesystems, integration tests covering complete workflows, dependency
auditing and linting in CI, recovery tests for corrupted files and failed
imports, conflict and external modification tests, and expanded threat-model
documentation. A user can install, initialize a vault, create encrypted
entries, search and retrieve secrets, synchronize by their chosen means,
export selected entries, and restore from backup using only the documentation.

## Commands available

`vault init`, `vault add`, `vault show`, `vault edit`, `vault delete`,
`vault list`, `vault search`, `vault get`, `vault env export`,
`vault env list`, `vault generate password`, `vault check`, `vault doctor`,
`vault copy`, `vault completion`, `vault config`, `vault backup`,
`vault restore`, `vault password change`, `vault export`, `vault import`

Run `vault --help` or `python -m cipherbox --help` for inline help.
