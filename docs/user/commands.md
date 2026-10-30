# Commands

Reference for the `vault` CLI commands.

## `vault init`

Initialize a vault directory, configuration, and required subdirectories.

```bash
vault init --path ./my-vault --confirm
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path (default: platform default vault dir) |
| `--confirm` | Overwrite an existing vault (required if it already exists) |

Refuses to overwrite an existing vault unless `--confirm` is passed.

## `vault add`

Add a new entry to the vault.

```bash
vault add --path ./my-vault --type login --title github \
  --field username=alice --field password=secret
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `--type` | Secret type (required): `login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery` |
| `--title` | Entry title (required) |
| `--field` | Field in `key=value` form (repeatable) |

If no `--field` is supplied, `add` prompts interactively for field names and values until you enter a blank field name.

Output:

```
Added entry <uuid> (github)
```

## `vault show`

Show an entry's metadata. Secret field values are redacted by default.

```bash
vault show --path ./my-vault <entry-id>
vault show --path ./my-vault <entry-id> --reveal
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `id` | Entry id (required) |
| `--reveal` | Reveal secret field values |

Example output (redacted):

```
id:        8f1d2c4b-a11e-4c2d-9e3f-5a6b7c8d9e0f
type:      login
title:     github
tags:      (none)
created:   2026-10-27T12:00:00Z
updated:   2026-10-27T12:00:00Z
fields:
  password: <redacted>
  username: <redacted>
```

## `vault edit`

Edit an existing entry. The `id` and `created_at` are preserved; `updated_at`
is refreshed.

```bash
vault edit --path ./my-vault <entry-id> --field password=newpass
```

Multiple fields can be updated by repeating `--field`:

```bash
vault edit --path ./my-vault <entry-id> \
  --field password=newpass --field username=bob
```

Field specs use `key=value` form. Invalid specs (missing `=`) return a
validation error (exit code 2).

Output:

```
Edited entry <uuid> (github)
```

## `vault delete`

Delete an entry. Confirmation is required unless `--confirm` is passed.

```bash
vault delete --path ./my-vault <entry-id> --confirm
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `id` | Entry id (required) |
| `--confirm` | Confirm the deletion |

Without `--confirm`:

```
error: deletion requires confirmation (pass --confirm)
```

Only the intended entry's file is removed.

## `vault list`

List vault entries with optional filters, sorting, pagination, and output format. Secret field values are redacted by default.

```bash
vault list --path ./my-vault
vault list --path ./my-vault --type api-key --tag development --output json
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `--type` | Filter by entry type (`login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery`) |
| `--tag` | Filter by tag (repeatable; an entry must carry every requested tag) |
| `--title` | Filter by exact title match |
| `--field` | Field to constrain (repeatable; pair with `--equals` or `--contains`) |
| `--equals` | Exact value for the corresponding `--field` (repeatable) |
| `--contains` | Substring value for the corresponding `--field` (repeatable) |
| `--sort` | Sort by `title`, `created`, or `updated` (default: `title`) |
| `--limit` | Maximum number of entries to return |
| `--offset` | Number of entries to skip |
| `--output` | Output format: `table` (default) or `json` |
| `--reveal` | Reveal secret field values |

Filters on different dimensions use AND semantics. Text search across title, fields, and tags is available via `vault search`.

## `vault backup`

Create, list, and restore vault backups. Backups are stored outside the active vault by default (a `<vault>-backups` sibling directory) and include `config.json` plus every entry file.

```bash
# Create a snapshot of the vault
vault backup create --path ./my-vault --backup-dir ./my-backups

# List available backups
vault backup list --path ./my-vault --backup-dir ./my-backups

# Restore a backup (non-destructive: refuses to overwrite existing entry files)
vault restore <backup-id> --path ./my-vault --backup-dir ./my-backups

# Preview what would be restored without writing
vault restore <backup-id> --path ./my-vault --backup-dir ./my-backups --dry-run
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `--backup-dir` | Directory to store/read backups (default: `<vault>-backups` sibling) |
| `<backup-id>` | Backup id to restore (required for `restore`) |
| `--dry-run` | Validate and report what would be restored without writing (restore only) |

`vault backup create` prints the new backup id. `vault restore` validates the
backup before restoring and never overwrites an entry file that already exists
in the active vault.

## Conflict handling

If two entry files resolve to the same stable entry ID (a synchronization
conflict), `vault list` raises a conflict error naming both files — neither
copy is silently dropped or merged. Use `vault backup` / `vault restore` to
recover manually.

## `vault search`

Search vault entries by text across title, fields, and tags (case-insensitive partial match).

```bash
vault search --path ./my-vault "github"
vault search --path ./my-vault "staging" --in fields --output json
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `<query>` | Text query (required; case-insensitive partial match) |
| `--in` | Comma-separated fields to search: `title`, `fields`, `tags` (default: `title,fields,tags`) |
| `--type` | Filter by entry type |
| `--tag` | Filter by tag (repeatable; AND semantics) |
| `--sort` | Sort by `title`, `created`, or `updated` (default: `title`) |
| `--limit` | Maximum number of entries to return |
| `--offset` | Number of entries to skip |
| `--output` | Output format: `table` (default) or `json` |
| `--reveal` | Reveal secret field values |

## `vault export`

Export all entries to a portable JSON document (`cipherbox-export/1` schema). Plaintext output — prints a warning to stderr and refuses to overwrite an existing file unless `--confirm` is passed.

```bash
vault export --path ./my-vault --output export.json
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `--output` | Output file path (required) |
| `--confirm` | Confirm overwrite of an existing output file |

## `vault import`

Import entries from a JSON export file. Validates every entry before writing anything — an invalid import never partially modifies the vault. Detects duplicate IDs and title collisions; supports `--policy skip|replace|rename` and `--dry-run`.

```bash
vault import export.json --path ./my-vault --policy skip --dry-run
vault import export.json --path ./my-vault --policy replace
```

| Argument | Description |
|----------|-------------|
| `<file>` | Import file path (required) |
| `--path` | Vault directory path |
| `--policy` | Collision policy: `skip`, `replace`, or `rename` (default: `skip`) |
| `--dry-run` | Report proposed changes without writing anything |

## `vault env export`

Export only entries explicitly tagged with a project to a `.env` file. Plaintext output — prints a warning to stderr and refuses to overwrite an existing file unless `--confirm`.

```bash
vault env export my-project --path ./my-vault --output .env --confirm
```

| Argument | Description |
|----------|-------------|
| `<project>` | Project tag to select entries for (required) |
| `--path` | Vault directory path |
| `--output` | Output `.env` file path (required) |
| `--confirm` | Confirm overwrite of an existing output file |

## `vault env list`

List entries tagged with a project, with field values redacted.

```bash
vault env list --path ./my-vault my-project
```

| Argument | Description |
|----------|-------------|
| `<project>` | Project tag to select entries for (required) |
| `--path` | Vault directory path |

## `vault get`

Retrieve a single secret field value to stdout (explicit retrieval only). Without `--field`, prints entry metadata with field values redacted. Missing entry or field returns a nonzero exit code; secret values are never printed to stderr.

```bash
vault get --path ./my-vault <entry-id> --field password
vault get --path ./my-vault <entry-id>
```

| Argument | Description |
|----------|-------------|
| `id` | Entry id (required) |
| `--path` | Vault directory path |
| `--field` | Print only this field's value to stdout |
| `--reveal` | Reveal secret field values in metadata view |

## `vault generate password`

Generate a secure password using a cryptographically secure random-number generator. Never auto-stored.

```bash
vault generate password --path ./my-vault --length 32
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `--length` | Password length (default: `32`) |
| `--charset` | Comma-separated charset pool: `lower`, `upper`, `digits`, `punctuation` (default: `lower,digits`) |

## `vault check`

Validate the vault: schema validity of every entry, duplicate IDs, malformed files, and encryption metadata status. Distinguishes warnings from errors; never exposes decrypted contents.

```bash
vault check --path ./my-vault --all
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |
| `--all` | Run all available checks |

## `vault doctor`

Diagnose vault configuration and filesystem permission problems.

```bash
vault doctor --path ./my-vault
```

| Argument | Description |
|----------|-------------|
| `--path` | Vault directory path |

## `vault copy`

Copy a single secret field value to the clipboard. Requires explicit `--field` selection. Prints a warning that clipboard contents may be accessible to other applications; clearing is best-effort and clipboard managers may retain copies.

```bash
vault copy --path ./my-vault <entry-id> --field token
```

| Argument | Description |
|----------|-------------|
| `id` | Entry id (required) |
| `--path` | Vault directory path |
| `--field` | Field whose value to copy (required) |

## `vault completion`

Generate shell completion scripts for `bash`, `zsh`, or `powershell`.

```bash
vault completion bash   > ~/.local/share/bash-completion/completions/vault
vault completion zsh    > ~/.zsh/completions/_vault
vault completion powershell
```

| Argument | Description |
|----------|-------------|
| `shell` | Shell to generate completion for: `bash`, `zsh`, or `powershell` |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation error |
| 3 | Entry not found |
| 4 | Duplicate ID |
| 5 | Confirmation required |

## Default vault location

If `--path` is omitted, the default vault location is used:

- Windows: `%LOCALAPPDATA%/cipherbox-vault`
- macOS/Linux: `$XDG_DATA_HOME/cipherbox-vault` or `~/.local/share/cipherbox-vault`
