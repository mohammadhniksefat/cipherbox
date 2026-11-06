"""``vault decrypt`` command: decrypt an existing encrypted vault in place."""

from __future__ import annotations

import argparse
import base64
import json
import sys

from cipherbox.config.paths import resolve_vault_dir
from cipherbox.crypto.kdf import kdf_params_from_dict
from cipherbox.crypto.keyring import KeyringStore
from cipherbox.crypto.vault import (
    CONFIG_FILE_NAME,
    VaultKeyManager,
    load_vault_crypto,
    prompt_password,
)
from cipherbox.storage.repository import VaultRepository

# Encryption metadata keys stored in config.json (never the key or password).
_CRYPTO_KEYS = {"encrypted", "kdf", "kdf_params", "salt"}


def _confirm(prompt: str, confirm: bool) -> bool:
    if confirm:
        return True
    answer = input(prompt).strip().lower()
    return answer == "y"


def decrypt_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """Decrypt an existing encrypted vault in place.

    Prompts for the current master password, unlocks the vault, reads every
    entry file (validating authentication before any writes), re-writes each
    entry file as plaintext JSON, and removes the encryption metadata from the
    vault config.
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
    if not meta.get("encrypted"):
        print("error: vault is not encrypted", file=sys.stderr)
        return 1

    if not _confirm(
        "Decrypting will rewrite all entry files as plaintext. Continue? (y/N): ",
        getattr(args, "confirm", False),
    ):
        print(
            "error: decryption requires confirmation (pass --confirm)", file=sys.stderr
        )
        return 5

    # Prompt for master password.
    password = prompt_password("Enter master password: ")

    # Derive the key from the stored salt and KDF parameters.
    salt = base64.b64decode(meta["salt"])
    params = kdf_params_from_dict(meta["kdf_params"])
    mgr = VaultKeyManager()
    try:
        mgr.unlock(password, salt, params)
    except Exception as exc:  # noqa: BLE001 - wrong password surfaces here
        print(f"error: unable to unlock vault: {exc}", file=sys.stderr)
        return 1

    # Read all entries while unlocked (validates decryption/authentication
    # before any plaintext is written to disk).
    unlocked_repo = VaultRepository(vault_path, key=mgr.key)
    entries = unlocked_repo.list()

    # Re-write every entry as plaintext JSON (atomic temp-file-then-replace).
    plain_repo = VaultRepository(vault_path)
    for entry in entries:
        plain_repo._write_entry_file(plain_repo._entry_path(entry.id), entry)

    # Remove encryption metadata from config, preserving other keys.
    config_file = vault_path / CONFIG_FILE_NAME
    config = json.loads(config_file.read_text(encoding="utf-8"))
    for key in _CRYPTO_KEYS:
        config.pop(key, None)
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

    # The old derived keyring entry no longer applies (vault is now plaintext).
    store = KeyringStore()
    store.erase(vault_path)

    mgr.lock()

    print(f"Decrypted {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}")
    return 0
