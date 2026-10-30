# Entry Schema

Each vault entry is a JSON object with a versioned schema.

## Schema version

Current schema version: `1`.

## Common fields

Every entry carries these metadata fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable UUID, independent of filename |
| `schema_version` | integer | Schema version (currently `1`) |
| `type` | string | Secret type: `login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery` |
| `title` | string | Human-readable title (required) |
| `tags` | array of string | Tags for organization/filtering |
| `created_at` | string | Creation timestamp (UTC) |
| `updated_at` | string | Last-update timestamp (UTC) |
| `fields` | object | Typed secret fields (key → string value) |

## Example entry

```json
{
  "id": "8f1d2c4b-a11e-4c2d-9e3f-5a6b7c8d9e0f",
  "schema_version": 1,
  "type": "login",
  "title": "github",
  "tags": [],
  "created_at": "2026-10-27T12:00:00Z",
  "updated_at": "2026-10-27T12:00:00Z",
  "fields": {
    "username": "alice",
    "password": "secret"
  }
}
```

## Validation

Entries are validated when read and written:

- `schema_version` must equal the current version (`1`).
- `type` must be a known secret type.
- `title` must be non-empty.
- Missing required fields or malformed JSON produce actionable errors.

Duplicate IDs are rejected on `add`. Editing preserves `id` and `created_at`
while refreshing `updated_at`.

## File format

Entries are stored as one JSON file per entry under `<vault>/entries/<uuid>.json`.
Writes are atomic (temp file in the same directory, then replace).

Once the vault is encrypted (Phase 3+), entry files are AES-256-GCM encrypted
envelopes (`cipherbox-vault-enc/1`) with base64 fields `format`, `algorithm`,
`nonce`, `aad`, and `ciphertext`. Entry fields are never written to disk in
plaintext once the vault is encrypted. Plaintext Phase 1 vaults remain
readable for backward compatibility.
