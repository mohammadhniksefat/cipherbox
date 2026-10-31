"""`vault password change` command: re-encrypt all entries with a new master password."""

from __future__ import annotations

import argparse
import base64
import os
import sys

from cipherbox.crypto.kdf import (
    default_kdf_params,
    derive_key,
    kdf_params_from_dict,
    kdf_params_to_dict,
)
from cipherbox.crypto.keyring import KeyringStore
from cipherbox.crypto.vault import (
    VaultKeyManager,
    load_vault_crypto,
    prompt_password,
    save_vault_crypto,
)
from cipherbox.storage.repository import VaultRepository


def _build_new_crypto_meta(new_password: str) -> tuple[dict, bytes]:
    """Derive a new key with a fresh random salt.

    Returns (config metadata dict, new key bytes).
    """
    salt = os.urandom(16)
    params = default_kdf_params()
    key = derive_key(new_password, salt, params)
    meta = {
        "encrypted": True,
        "kdf": "argon2id",
        "kdf_params": kdf_params_to_dict(params),
        "salt": base64.b64encode(salt).decode("ascii"),
    }
    return meta, key


def password_change_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """Change the vault master password and re-encrypt every entry.

    Unlocks with the current password (hidden prompt), reads all entries,
    derives a new key with a fresh salt from the new password, re-encrypts
    every entry, persists the new crypto metadata, and zeroizes the old key.
    """
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    vault_dir = repo.vault_path

    # Load current crypto metadata.
    try:
        meta = load_vault_crypto(vault_dir)
    except FileNotFoundError:
        print("error: vault is not initialized", file=sys.stderr)
        return 1
    if not meta.get("encrypted"):
        print("error: vault is not encrypted", file=sys.stderr)
        return 1

    # Unlock with the current password (hidden prompt). Wrong password
    # derives a wrong key, which surfaces as DecryptionError when entries
    # are decrypted below (and is surfaced by main() as a CLI error).
    old_password = prompt_password("Enter current master password: ")
    salt = base64.b64decode(meta["salt"])
    params = kdf_params_from_dict(meta["kdf_params"])
    mgr = VaultKeyManager()
    mgr.unlock(old_password, salt, params)

    # Read all entries while unlocked with the old key.
    unlocked_repo = VaultRepository(repo.vault_path, key=mgr.key)
    entries = unlocked_repo.list()

    # Prompt new password with confirmation.
    new_password = prompt_password("Enter new master password: ")
    confirm_password = prompt_password("Confirm new master password: ")
    if new_password != confirm_password:
        print("error: password confirmation does not match", file=sys.stderr)
        mgr.lock()
        return 1

    # Derive new key with a fresh random salt.
    new_meta, new_key = _build_new_crypto_meta(new_password)

    # Re-encrypt every entry with the new key. Remove old entry files first
    # because add() rejects duplicate IDs. All deletions/re-encryptions use
    # the old key while still unlocked.
    new_repo = VaultRepository(vault_dir, key=new_key)
    for entry in entries:
        unlocked_repo.delete(entry.id, confirm=True)
    for entry in entries:
        new_repo.add(entry)

    # Persist new crypto metadata.
    save_vault_crypto(vault_dir, new_meta)

    # Zeroize old key material.
    mgr.lock()

    # Invalidate the stale keyring entry (old derived key can no longer
    # unlock anything) and offer to store the new derived key.
    store = KeyringStore()
    store.erase(vault_dir)

    restore = prompt_password("Store new unlock key in keyring? (y/N): ")
    if restore.strip().lower() == "y":
        store.store(vault_dir, new_key)
        print(f"Stored unlock key for vault at {vault_dir}")
    else:
        print(f"Unlock key not stored for vault at {vault_dir}")

    count = len(entries)
    print(
        f"Changed master password; re-encrypted {count} entr{'y' if count == 1 else 'ies'}"
    )
    return 0
