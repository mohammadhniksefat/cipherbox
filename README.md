# cipherbox

Local-first CLI secrets manager. Stores one JSON file per secret in a local
vault directory.

**Status:** Phase 7 (release hardening and documentation) complete — stable MVP
release. Entry files are stored as authenticated AES-GCM envelopes derived from
a master password via Argon2id. Writes are atomic (temp file + fsync + replace
in the same directory). Duplicate entry IDs across files are detected as sync
conflicts and never silently resolved. Backups and restore are available via
`vault backup` / `vault restore`. Plaintext Phase 1 vaults remain readable for
backward compatibility.

## Install

```bash
pip install cipherbox
```

or from source:

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

# Retrieve a single secret field value to stdout (explicit retrieval only)
vault get --path ./my-vault <entry-id> --field password

# List project-tagged env entries (values redacted)
vault env list --path ./my-vault my-project

# Generate a secure password with a CSPRNG (never auto-stored)
vault generate password --path ./my-vault --length 32

# Validate the vault: schema, duplicate IDs, malformed files
vault check --path ./my-vault --all

# Diagnose vault configuration and filesystem permissions
vault doctor --path ./my-vault

# Copy a secret field value to the clipboard (explicit field required)
vault copy --path ./my-vault <entry-id> --field token

# Copy a secret field value to the clipboard (explicit field required)
vault copy --path ./my-vault <entry-id> --field token

# Export all entries to a portable JSON document (plaintext: warns on stderr)
vault export --path ./my-vault --output export.json

# Import entries into a vault (validate-before-write; skip/replace/rename policies)
vault import export.json --path ./my-vault --policy skip --dry-run
vault import export.json --path ./my-vault --policy replace

# Export project-tagged entries to a .env file (plaintext: warns on stderr)
vault env export my-project --path ./my-vault --output .env --confirm
```

# Default vault (optional)

To avoid passing `--path` on every command, set a default vault in app-level
config (stored outside any vault):

```bash
vault config set default-vault ./my-vault
vault list          # operates on ./my-vault without --path
vault config list   # show all configured keys
vault config unset default-vault   # restores platform default
```

If `--path` is omitted and no default vault is configured, the platform default
location is used (`%LOCALAPPDATA%/cipherbox-vault` on Windows,
`$XDG_DATA_HOME/cipherbox-vault` or `~/.local/share/cipherbox-vault` elsewhere).
`--path` always overrides both. App config lives at
`%LOCALAPPDATA%/cipherbox/app-config.json` (Windows) or
`$XDG_CONFIG_HOME/cipherbox/app-config.json` (`~/.config/cipherbox/app-config.json`
elsewhere), separate from per-vault `config.json`.

## Secret types

`login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery`.

Each entry carries: `id`, `schema_version`, `type`, `title`, `tags`,
`created_at`, `updated_at`, `fields`. Identifiers are stable UUIDs independent
of filenames; timestamps are UTC.

## Vault layout

```
<vault>/
├── config.json        # vault configuration (includes encryption metadata when encrypted)
└── entries/           # one JSON file per entry
    └── <uuid>.json    # AES-GCM encrypted envelope when the vault is encrypted
```

Each entry file is either a plaintext JSON object (backward-compatible Phase 1
vaults) or an encrypted envelope (`cipherbox-vault-enc/1`) with base64 fields
`format`, `algorithm`, `nonce`, `aad`, and `ciphertext`. Entry fields are never
written to disk in plaintext once the vault is encrypted.

Writes are atomic (temp file + replace in the same directory).

## Backup and restore

```bash
# Create a snapshot of the vault (stored outside the active vault by default)
vault backup create --path ./my-vault --backup-dir ./my-backups

# List available backups
vault backup list --path ./my-vault --backup-dir ./my-backups

# Restore a backup (non-destructive: refuses to overwrite existing entry files)
vault restore <backup-id> --path ./my-vault --backup-dir ./my-backups

# Preview what would be restored without writing
vault restore <backup-id> --path ./my-vault --backup-dir ./my-backups --dry-run
```

`vault backup create` snapshots `config.json` plus every entry file into a
timestamped directory under the backup dir (default: `./my-vault-backups`).
`vault restore` validates the backup before restoring and never overwrites an
entry file that already exists in the active vault — use `--dry-run` to preview
without writing.

## Import and export

```bash
# Export all entries to a portable JSON document (plaintext: warns on stderr)
vault export --path ./my-vault --output export.json

# Import entries into a vault (validate-before-write; never partially modifies
# the vault on a bad import; skip/replace/rename collision policies)
vault import export.json --path ./my-vault --policy skip --dry-run
vault import export.json --path ./my-vault --policy replace

# Export only entries tagged with a project to a .env file (plaintext: warns
# on stderr; refuses to overwrite an existing file unless --confirm)
vault env export my-project --path ./my-vault --output .env --confirm
```

`vault export` writes a `cipherbox-export/1` document containing every entry's
supported fields. `vault import` validates every entry before writing anything,
detects duplicate IDs and title collisions, and supports `--dry-run` to preview
proposed changes. `vault env export` selects entries explicitly tagged with the
given project — unrelated secrets are never exported.

Both `vault export` and `vault env export` print a plaintext warning to stderr
and refuse to overwrite an existing output file unless `--confirm` is passed.

## Conflict handling

If two entry files resolve to the same stable ID (a synchronization conflict),
`vault list` raises a conflict error naming both files — neither copy is
silently dropped. Use `vault backup` / `vault restore` to recover manually.
Automatic merging is not performed.

## Encryption at rest

`vault init` creates the vault directory and `config.json`. Encryption metadata
(`encrypted=true`, `kdf`, `kdf_params`, random base64 `salt`) is persisted into
`config.json` when the repository is bound with a derived master key. From then on,
every data-accessing command (`add`, `list`, `search`, `show`, `get`, `edit`,
`delete`) reads the master password through a hidden `getpass` prompt — it is
never accepted as a CLI argument — derives a key with Argon2id (`argon2id`,
default `time_cost=3`, `memory_cost=65536`, `parallelism=4`, `hash_len=32`), and
holds it only in memory for the duration of the command.

Entry files are AES-256-GCM encrypted envelopes with a fresh 12-byte random
nonce per write. Critical metadata (format, algorithm, schema version) is
authenticated as associated data (AAD), so any tampering with the envelope is
rejected — never silently decoded. Wrong password or a locked vault fails
closed: the command errors out and no plaintext is returned.

### `vault password change`

```bash
vault password change --path ./my-vault --confirm
```

Prompts for the old password (hidden), unlocks and reads every entry, prompts
for the new password (hidden, with confirmation), derives a new key with a
fresh random salt, re-encrypts every entry, updates the vault config metadata,
and zeroizes the old key. After the change, the old password no longer unlocks
the vault and the new password does, with all entry contents intact.

## Security notes

- Entry files are **authenticated AES-GCM envelopes**, never plaintext, once
  the vault is encrypted. Plaintext Phase 1 vaults remain readable for
  backward compatibility.
- The master password is read through a hidden prompt only; it is never logged,
  never written to disk, and never accepted as a CLI argument.
- Key material is held only in memory for the duration of the command and is
  zeroized (best-effort) before exit.
- Wrong password or a locked vault fails closed — no partial plaintext, no
  silent fallback.
- Never store real credentials in a vault you have not verified is encrypted.
- Explicitly retrieved values (`vault get`, `vault copy`) can still leak through
  terminal history, shell logs, pipelines, and clipboard managers; treat them
  like secrets once on screen or in the clipboard.

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

## Developer productivity

```bash
# Retrieve a single secret field value to stdout (explicit retrieval only)
vault get --path ./my-vault <entry-id> --field password

# List project-tagged env entries (values redacted)
vault env list --path ./my-vault my-project

# Generate a secure password with a CSPRNG (never auto-stored)
vault generate password --path ./my-vault --length 32

# Validate the vault: schema, duplicate IDs, malformed files
vault check --path ./my-vault --all

# Diagnose vault configuration and filesystem permissions
vault doctor --path ./my-vault

# Copy a secret field value to the clipboard (explicit field required)
vault copy --path ./my-vault <entry-id> --field token
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

1. Foundation (structure, formats, contracts) — **complete**
2. Storage and CRUD (plaintext prototype) — **complete**
3. Search and filtering — **complete**
4. Encryption at rest — **complete**
5. Import, export, and portability — **complete**
6. Developer productivity features — **complete**
7. Release hardening — **complete**

## Shell completion

Generate completion for your shell:

```bash
vault completion bash   # source into your bash completion dir
vault completion zsh    # source into your zsh completions
vault completion powershell
```

See `docs/release.md` for install and source instructions.

## License

Personal project.
