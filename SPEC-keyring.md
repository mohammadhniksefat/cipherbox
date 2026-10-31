# Spec: Keyring-based unlock persistence for cipherbox

## Objective

Let a personal user store an encrypted vault's **derived AES-256 key** in the OS keyring so subsequent `vault` commands unlock without a password prompt. Opt-in via explicit commands (`vault keyring store|clear|show`); default behavior (prompt every time) unchanged. The derived key — never the master password — is stored in the keyring. On password change, the user is prompted to re-store the new key; the stale entry is removed.

## Tech Stack

- Python 3.11+, stdlib preferred
- Existing deps: `argon2-cffi`, `cryptography`
- New optional dep: `keyring` (cross-platform access to OS credential stores)
- Tests: `pytest`, `ruff`

## Commands

| Command | Behavior |
|---|---|
| `vault keyring store --path <vault>` | Prompt for master password (hidden), unlock vault to derive key, store derived key in OS keyring keyed by vault path. `--path` optional; falls back to app config `default-vault`, then platform default vault dir. Exit 0 on success; nonzero if vault not encrypted or wrong password. |
| `vault keyring clear --path <vault>` | Remove keyring entry for vault path. Exit 0 regardless of whether entry existed. `--path` optional, same fallback as store. |
| `vault keyring show --path <vault>` | Print whether a keyring entry exists for this vault path (yes/no, no secret exposed). Exit 0. `--path` optional, same fallback. |
| `vault list|show|get|edit|delete|search --path <vault>` | Unlock resolution: keyring → `VAULT_PASSWORD` env var → `getpass` prompt. Default unchanged (prompt if nothing cached). |
| `vault password change --path <vault> --confirm` | Existing behavior (re-encrypt all entries with new key) **plus** delete stale keyring entry and prompt to re-store the new derived key. |

## Project Structure

```
src/cipherbox/crypto/keyring.py          # NEW: OS keyring get/set/erase wrapper
src/cipherbox/cli/keyring.py             # NEW: keyring store|clear|show commands
src/cipherbox/cli/unlock.py              # NEW: key/keyring resolution (keyring → env → prompt)
src/cipherbox/__main__.py                # MODIFY: register keyring subcommand; _repo() uses unlock resolution
src/cipherbox/cli/password.py            # MODIFY: password_change_command clears + offers to re-store keyring entry
tests/test_cli_keyring.py                # NEW: unit tests for keyring commands
tests/test_unlock.py                     # NEW: unit tests for unlock resolution
docs/user/security.md                    # MODIFY: document keyring trade-offs
docs/user/commands.md                    # MODIFY: add keyring command reference
```

## Code Style

Follow existing conventions: `from __future__ import annotations`, type hints, Google-style docstrings, ruff format/lint.

Example:

```python
def resolve_vault_key(vault_path: Path) -> bytes | None:
    """Resolve the decryption key for an encrypted vault.

    Priority:
      1. OS keyring entry for vault path (derived key, no prompt)
      2. VAULT_PASSWORD environment variable (derive via Argon2id)
      3. Hidden getpass prompt (derive via Argon2id)
    """
    ...
```

## Testing Strategy

- Unit tests for `keyring.py`: store/get/erase round-trip; missing entry returns None; unsupported backend handled gracefully.
- Unit tests for `unlock.py`: keyring hit skips prompt; env var derives key; prompt fallback; wrong password → error.
- Integration tests via `main()`: `vault keyring store` then `vault list` without prompt; `vault keyring clear` restores prompt behavior; `vault password change` clears stale entry and offers re-store.
- Mock `keyring` backend where appropriate to avoid real OS keyring side effects in CI.
- Full suite green: `python -m pytest`, `ruff check`, `ruff format --check`.

## Boundaries

**Always do:**
- Default behavior unchanged: no keyring entry → `getpass` prompt every command.
- Never store master password in keyring; only the derived AES key.
- Never store master password or derived key in app config (`app-config.json`) or plaintext files.
- Wrong password → `DecryptionError`, nonzero exit, no partial plaintext.
- `vault password change` invalidates the stale keyring entry and prompts to re-store.

**Ask first about:**
- Adding the `keyring` dependency (new third-party package).
- Behavior on headless/CI machines where keyring daemon may be unavailable (fall back to env var or prompt).

**Never do:**
- Auto-store to keyring without explicit `vault keyring store`.
- Change `vault init --path` behavior.
- Weaken fail-closed decryption.

## Success Criteria

- [ ] `vault keyring store --path <encrypted-vault>` prompts for password, stores derived key, exits 0.
- [ ] After store, `vault list --path <encrypted-vault>` exits 0 without prompting.
- [ ] `vault keyring clear --path <encrypted-vault>` removes entry; subsequent `vault list` prompts again.
- [ ] `vault keyring store` / `clear` / `show` work without `--path` using default vault resolution.
- [ ] `vault password change` removes stale keyring entry and prompts to re-store the new key.
- [ ] Full suite green: tests pass, ruff clean, format clean.

## Open Questions

None — all resolved:
- Command group: `vault keyring store|clear|show`
- `--path` optional, falls back to default vault
- `password change` prompts to re-store new key

## Approval

Approved by user on 2026-10-31. Ready for plan → implement.
