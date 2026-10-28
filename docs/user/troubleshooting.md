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

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation error |
| 3 | Entry not found |
| 4 | Duplicate ID |
| 5 | Confirmation required |
