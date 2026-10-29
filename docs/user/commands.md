# Commands

Reference for the `vault` CLI commands available in Phase 1.

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
