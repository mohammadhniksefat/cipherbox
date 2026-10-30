# Security

## Current status

**Encryption at rest is active (Phase 3 complete).** Entry files are stored as
authenticated AES-GCM envelopes derived from a master password via Argon2id.
Writes are atomic; duplicate entry IDs across files are detected as sync
conflicts and never silently resolved; backups and restore are available via
`vault backup` / `vault restore`. Plaintext Phase 1 vaults remain readable for
backward compatibility but new vaults are encrypted.

- The master password is read through a hidden `getpass` prompt — never a CLI
  argument — derived once per command with Argon2id, kept only in memory during
  process execution, and discarded before exit.
- Entry files are AES-256-GCM encrypted envelopes with a fresh 12-byte random
  nonce per write. Critical metadata (format, algorithm, schema version) is
  authenticated as associated data (AAD), so any tampering with the envelope is
  rejected — never silently decoded. Wrong password or a locked vault fails
  closed: the command errors out and no plaintext is returned.
- Key material is held only in memory for the duration of the command and is
  zeroized (best-effort) before exit.
- `vault password change` re-encrypts every entry with a new key and invalidates
  the old password.

## Threat-model limitations

cipherbox is designed to protect secrets at rest on a host you trust and
control. It is **not** a defense against a compromised host.

- Anyone with read access to the vault directory can attempt to decrypt entry
  files; the master password is the sole gate.
- Malware running under your user account can read the vault directory,
  capture the master password at the hidden `getpass` prompt, read terminal
  scrollback and shell history, access the clipboard, and read decrypted
  secrets in memory while a cipherbox command runs. Encryption at rest does
  not protect against malware on the same host — protect the host itself.
- Terminal history, shell pipelines, and logs may capture explicitly retrieved
  secret values (e.g. `vault show --reveal`, `vault get`, `vault copy`).
- Clipboard contents (`vault copy`) may be accessible to other applications;
  clearing is best-effort and clipboard managers may retain copies.
- Exported `.env` files and JSON exports store secret values in plaintext;
  protect them like secrets and never commit them to version control.
- Deleting an export does not guarantee secure erasure from storage media or
  backups.

In short: treat the machine running cipherbox as part of your trust boundary,
and treat any explicitly retrieved value (on screen or in the clipboard) as a
secret once it leaves the vault.

## Best practices

- Keep the vault directory on a filesystem you control and restrict its
  permissions.
- Do not store real credentials in a vault you have not verified is encrypted.
- Treat explicitly retrieved values (`vault show --reveal`, `vault get`,
  `vault copy`) as sensitive: avoid redirecting them to files or including them
  in scripts that log output.
- Protect `.env` exports and JSON exports like secrets; never commit them to
  version control.
- Keep backups of your vault and store them securely; test restore periodically.
