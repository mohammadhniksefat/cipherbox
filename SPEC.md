# Spec: Vault Config Manager & Default Vault Resolution

## Objective

Let a personal user designate a **default vault** so commands run without `--path` operate against it, while still allowing explicit `--path` to target any other vault. App-level config is stored separately from per-vault `config.json`, following a git-like `vault config show|set|unset <key>` interface. MVP stores only `default-vault`; the config manager is key-value so future keys can be added without new commands.

## Target user

Single personal user managing one or more local vault directories.

## Commands

### `vault config show <key>`

Print the configured value for `<key>` (e.g. `default-vault`).
- If key exists: print the path, exit 0.
- If key missing: print error to stderr, exit nonzero.
- Unknown key: same as missing.

### `vault config set <key> <value>`

Store `<key>` = `<value>` in app config.
- Exit 0 on success; print nothing or a short confirmation to stdout.
- If value missing: error to stderr, exit nonzero.

### `vault config unset <key>`

Remove `<key>` from app config.
- Exit 0 on success regardless of whether key existed.
- Missing key is not an error.

### Default vault resolution (applied to all data commands)

When `--path` is omitted:
1. Read app config `default-vault` key; if set, use that path.
2. Otherwise, fall back to `default_vault_dir()` (platform default).

When `--path` is given, it always wins over app config.

## Project structure

```
src/cipherbox/config/app_config.py      # NEW: app-level key-value config (default-vault)
src/cipherbox/config/paths.py           # MODIFY: resolve default vault from app config
src/cipherbox/cli/config.py             # NEW: vault config show|set|unset CLI
src/cipherbox/__main__.py               # MODIFY: register `config` subcommand; default-vault resolution in _repo()

tests/test_config.py                    # NEW: app_config unit tests
tests/test_cli_config.py                # NEW: config CLI tests
tests/test_default_vault_resolution.py  # NEW: resolution behavior via main()
```

App config location:
- Windows: `%LOCALAPPDATA%/cipherbox/app-config.json`
- Unix: `$XDG_CONFIG_HOME/cipherbox/app-config.json` or `~/.config/cipherbox/app-config.json`

This is separate from per-vault `config.json` (vault_dir/config.json) to avoid conflating app settings with vault encryption metadata.

## Code style

- Follow existing codebase conventions: `from __future__ import annotations`, type hints, Google-style docstrings, ruff format/lint.
- CLI commands follow `(args: argparse.Namespace, repo: VaultRepository | None = None) -> int` pattern where applicable.
- Config manager is pure file I/O (json), no crypto, no dependencies beyond stdlib.
- App config file created lazily on first `set`; missing file treated as empty config.
- Atomic write for app config (temp file + replace), consistent with repository writes.
- Secret values never printed to stderr.

## Testing strategy

- Unit tests for `app_config.py`: set/get/unset round-trip, missing file, corrupt JSON, atomic write, concurrent-safe temp file.
- CLI tests for `config.py`: show/set/unset exit codes, stdout/stderr content, missing args.
- Integration tests via `main()`: `vault config set default-vault <path>` then `vault list` (no `--path`) reads that vault; `vault config unset default-vault` restores platform-default behavior; `--path` overrides app config.
- Full suite must stay green: `python -m pytest`, `ruff check`, `ruff format --check`.

## Boundaries

**Always do:**
- Treat app config as untrusted user input; validate JSON on read.
- Never print secret values to stderr.
- `--path` always overrides app config default.

**Ask first about:**
- Adding config keys beyond `default-vault`.
- Encrypting app config (contains paths, not secrets, but still PII-ish).
- Auto-migrating entries between vaults.

**Never do:**
- Auto-delete or auto-overwrite a vault without `--confirm`.
- Store master password or keys in app config.
- Change behavior of `vault init --path` (it still initializes the given path regardless of default-vault).
