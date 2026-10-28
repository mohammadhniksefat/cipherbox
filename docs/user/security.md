# Security

## Current status

**Phase 1 stores entries in plaintext.** This is a development prototype for
validating the storage model, not the final default.

- Do **not** migrate real credentials into an unencrypted vault.
- Encryption at rest (master password + Argon2id key derivation + authenticated
  encryption) is planned for Phase 3.
- The master password will be derived once per command, kept only in memory
  during process execution, and discarded when the process exits.

## Threat-model limitations (Phase 1)

- Anyone with read access to the vault directory can read all secret values.
- Secret values are written to disk in plaintext JSON.
- Terminal history, shell pipelines, and logs may capture explicitly retrieved
  secret values (e.g. `vault show --reveal`, `vault get`).

## Best practices while using the plaintext prototype

- Keep the vault directory on a filesystem you control and restrict its
  permissions.
- Do not back up plaintext vaults to untrusted locations or sync them to
  cloud storage without encryption.
- Treat `vault show --reveal` output as sensitive: avoid redirecting it to
  files or including it in scripts that log output.

## Planned security (Phase 3)

- Master password prompted (hidden input, never a command-line argument).
- Argon2id key derivation with random salt.
- Authenticated encryption for entry files.
- Secret values hidden by default; revealed only through explicit retrieval.
- Password changes re-encrypt all entries and invalidate the old password.
