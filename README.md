# cipherbox

Local-first CLI secrets manager. Stores one JSON file per secret in a local
vault directory.

**Status:** Phase 1 (plaintext storage engine and CRUD) complete. Plaintext is
a development prototype only — do not migrate real credentials into an
unencrypted vault.

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

# Delete an entry (confirmation required)
vault delete --path ./my-vault <entry-id> --confirm

# List entries, redacted table by default
vault list --path ./my-vault
vault list --path ./my-vault --type api-key --tag development --output json

# Search entries by text across title, fields, and tags (case-insensitive)
vault search --path ./my-vault "github"
vault search --path ./my-vault "staging" --in fields --output json
```

If `--path` is omitted, the default vault location is used
(`%LOCALAPPDATA%/cipherbox-vault` on Windows,
`$XDG_DATA_HOME/cipherbox-vault` or `~/.local/share/cipherbox-vault` elsewhere).

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

## Listing and search

```bash
# List all entries (redacted table)
vault list --path ./my-vault

# Filter by type and tags (AND semantics: entry must carry every --tag)
vault list --path ./my-vault --type api-key --tag development

# Exact title match
vault list --path ./my-vault --title github

# Field query against typed entry data
vault list --path ./my-vault --field provider --equals openai
vault list --path ./my-vault --field hostname --contains staging

# Sort and paginate
vault list --path ./my-vault --sort updated --limit 10 --offset 0

# Machine-readable JSON output (secret values redacted unless --reveal)
vault list --path ./my-vault --output json --reveal

# Text search (case-insensitive partial match across title, fields, tags)
vault search --path ./my-vault "github"
vault search --path ./my-vault "staging" --in fields --output json
```

## Development

```bash
python -m pip install -e .          # install editable
python -m pytest                    # run all tests
python -m cipherbox                 # run the CLI (alias for `vault`)
vault --help                        # CLI help
```

The project follows a modular Python layout under `src/cipherbox/`
(`cli`, `config`, `domain`, `storage`, `crypto`, `services`,
`import_export`, `backup`) with `__main__.py` as the entry point.

## Roadmap

The project is developed in phases (see `docs/project-spec.md`):

1. Foundation (structure, formats, contracts)
2. Storage and CRUD (plaintext prototype) — **complete**
3. Search and filtering — **complete**
4. Encryption at rest
5. Safe writes and synchronization compatibility
6. Import, export, and portability
7. Release hardening

## License

Personal project. See `CONSTITUTION.md` for community guidelines.
