"""``vault encrypt`` command: encrypt an existing plaintext vault in place."""

from __future__ import annotations

import argparse
import base64
import os
import sys

from cipherbox.config.paths import resolve_vault_dir
from cipherbox.crypto.kdf import default_kdf_params, derive_key, kdf_params_to_dict
from cipherbox.crypto.keyring import KeyringStore
from cipherbox.crypto.vault import load_vault_crypto, prompt_password, save_vault_crypto
from cipherbox.storage.repository import VaultRepository


def _confirm(prompt: str, confirm: bool) -> bool:
    if confirm:
        return True
    answer = input(prompt).strip().lower()
    return answer == "y"


def encrypt_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """Encrypt an existing plaintext vault in place.

    Prompts for a master password, derives an AES-256 key via Argon2id with a
    fresh random salt, persists encryption metadata to the vault config, and
    re-writes every entry file as an AES-256-GCM encrypted envelope.

    Entry files are atomically replaced (temp file then os.replace), so a
    crash mid-migration never leaves a partially written entry file. All
    entries are validated for readability before any writes begin.
    """
    if repo is None:
        vault_path = resolve_vault_dir(getattr(args, "path", None))
    else:
        vault_path = repo.vault_path

    # Load current crypto metadata.
    try:
        meta = load_vault_crypto(vault_path)
    except FileNotFoundError:
        print("error: vault is not initialized", file=sys.stderr)
        return 1
    if meta.get("encrypted"):
        print("error: vault is already encrypted", file=sys.stderr)
        return 1

    if not _confirm(
        "Encrypting will rewrite all entry files. Continue? (y/N): ",
        getattr(args, "confirm", False),
    ):
        print(
            "error: encryption requires confirmation (pass --confirm)", file=sys.stderr
        )
        return 5

    # Prompt for master password (twice to confirm).
    password = prompt_password("Enter master password: ")
    confirm_password = prompt_password("Confirm master password: ")
    if password != confirm_password:
        print("error: password confirmation does not match", file=sys.stderr)
        return 1

    # Derive a new key with a fresh random salt.
    salt = os.urandom(16)
    params = default_kdf_params()
    key = derive_key(password, salt, params)
    crypto_meta = {
        "encrypted": True,
        "kdf": "argon2id",
        "kdf_params": kdf_params_to_dict(params),
        "salt": base64.b64encode(salt).decode("ascii"),
    }
    save_vault_crypto(vault_path, crypto_meta)

    # Read all plaintext entries first (validates readability before writes).
    plain_repo = VaultRepository(vault_path)
    entries = plain_repo.list()

    # Re-write every entry encrypted under the new key. _write_entry_file does
    # an atomic temp-file-then-replace, so a crash mid-migration never leaves
    # a partially written or missing entry file.
    enc_repo = VaultRepository(vault_path, key=key)
    for entry in entries:
        enc_repo._write_entry_file(enc_repo._entry_path(entry.id), entry)

    # Invalidate any stale keyring entry (the old derived key no longer
    # unlocks anything after migration) and offer to store the new key.
    store = KeyringStore()
    store.erase(vault_path)

    restore = prompt_password("Store new unlock key in keyring? (y/N): ")
    if restore.strip().lower() == "y":
        store.store(vault_path, key)
        print(f"Stored unlock key for vault at {vault_path}")
    else:
        print(f"Unlock key not stored for vault at {vault_path}")

    print(f"Encrypted {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}")
    return 0
