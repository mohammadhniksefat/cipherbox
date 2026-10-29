# Getting Started

`cipherbox` is a local-first CLI secrets manager. It stores one JSON file per
secret in a local vault directory and provides the `vault` command (also
runnable as `python -m cipherbox`).

## Install

```bash
git clone <repo>
cd cipherbox-py
python -m pip install -e .
```

This provides the `vault` command:

```bash
vault --help
```

Or run the CLI directly:

```bash
python -m cipherbox --help
```

## Initialize a vault

```bash
vault init --path ./my-vault --confirm
```

- `--path` sets the vault directory. If omitted, the default location is used:
  - Windows: `%LOCALAPPDATA%/cipherbox-vault`
  - macOS/Linux: `$XDG_DATA_HOME/cipherbox-vault` or `~/.local/share/cipherbox-vault`
- `--confirm` is required to overwrite an existing vault.

Output:

```
Initialized vault at ./my-vault
```

## Quick start

```bash
# Initialize a vault
vault init --path ./my-vault --confirm

# Add a login entry (fields supplied on the command line)
vault add --path ./my-vault --type login --title github \
  --field username=alice --field password=secret

# Show metadata (secret values redacted by default)
vault show --path ./my-vault <entry-id>

# Reveal secret values explicitly
vault show --path ./my-vault <entry-id> --reveal

# Edit an entry (id and created_at are preserved)
vault edit --path ./my-vault <entry-id> --field password=newpass

# Edit an entry (id and created_at are preserved)
vault edit --path ./my-vault <entry-id> --field password=newpass

# Delete an entry (confirmation required)
vault delete --path ./my-vault <entry-id> --confirm

# List entries (redacted table by default)
vault list --path ./my-vault
vault list --path ./my-vault --type api-key --tag development --output json

# Search entries by text (case-insensitive across title, fields, tags)
vault search --path ./my-vault "github"
vault search --path ./my-vault "staging" --in fields --output json
```

If `--path` is omitted, the default vault location is used.

## Phase status

**Phase 2 (search, filtering, and developer querying) complete.** Plaintext is a
development prototype only — do not migrate real credentials into an
unencrypted vault. Encryption at rest is planned for Phase 3.

## Secret types

`login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery`.

Each entry carries: `id`, `schema_version`, `type`, `title`, `tags`,
`created_at`, `updated_at`, `fields`. Identifiers are stable UUIDs independent
of filenames; timestamps are UTC.

## Vault layout

```
<vault>/
├── config.json        # vault configuration
└── entries/           # one JSON file per entry
    └── <uuid>.json
```

Writes are atomic (temp file + replace in the same directory).

## Security notes

- Phase 1 stores entries **in plaintext**. This is a development prototype
  for validating the storage model, not the final default.
- Encryption at rest (master password + Argon2id + authenticated encryption)
  is planned for Phase 3.
- Never store real credentials in an unencrypted vault.
