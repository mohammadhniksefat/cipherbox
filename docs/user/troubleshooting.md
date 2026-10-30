# Troubleshooting

## "vault already exists" error

```
error: vault already exists at ./my-vault; pass --confirm to overwrite
```

Pass `--confirm` to overwrite an existing vault, or choose a different `--path`.

## Entry not found (exit code 3)

```
error: entry <id> not found
```

The entry ID does not exist in the vault. Verify the ID with `vault list` (or
by inspecting `<vault>/entries/`).

## Invalid field spec (exit code 2)

```
error: invalid field spec 'password' (use key=value)
```

Field arguments must use `key=value` form, e.g. `--field password=secret`.

## Unknown secret type (exit code 2)

```
error: unknown secret type 'foo'
```

Valid types: `login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery`.

## Malformed entry file

If an entry file contains invalid JSON or fails schema validation, it is
skipped during listing and produces an error when accessed directly. Restore
the file from backup or remove the malformed file manually.

## Field not found (exit code 1)

```
error: entry <id> has no field '<field>'
```

The field name does not exist on the entry. List the entry's fields with
`vault show <id>` to see available field names.

## Missing entry (exit code 3)

```
error: entry <id> not found
```

The entry ID does not exist in the vault. Verify the ID with `vault list` (or
by inspecting `<vault>/entries/`).

## Invalid field spec (exit code 2)

```
error: invalid field spec 'password' (use key=value)
```

Field arguments must use `key=value` form, e.g. `--field password=secret`.

## Unknown secret type (exit code 2)

```
error: unknown secret type 'foo'
```

Valid types: `login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery`.

## Output file already exists (export / env export)

```
error: output file <path> already exists; pass --confirm to overwrite
```

`vault export` and `vault env export` refuse to overwrite an existing file
unless `--confirm` is passed. This prevents silently overwriting a previous
export.

## Invalid import (vault unchanged)

```
error: ... ImportError
```

An import that fails schema validation does not modify the vault at all.
Verify the export file uses the `cipherbox-export/1` schema and that every
entry has a valid `type`, `title`, and required fields.

## Duplicate ID / title collision (import)

When importing, duplicate IDs and title collisions are detected and handled
according to the chosen `--policy` (`skip`, `replace`, or `rename`). Use
`--dry-run` to preview proposed changes before writing.

## Encrypted vault requires a password

For commands that access protected data on an encrypted vault, the master
password is read through a hidden prompt. If the password is wrong, the
command errors out with exit code 1 and no plaintext is returned.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation error |
| 3 | Entry not found |
| 4 | Duplicate ID |
| 5 | Confirmation required |
