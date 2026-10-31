"""Vault unlock resolution: keyring -> env var -> getpass prompt.

Resolves the decryption key for an encrypted vault without always
prompting. The derived AES-256 key (never the master password) may be
cached in the OS keyring via ``vault keyring store``.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cipherbox.crypto.kdf import derive_key, kdf_params_from_dict
from cipherbox.crypto.keyring import KeyringStore
from cipherbox.crypto.vault import VaultKeyManager, load_vault_crypto, prompt_password
from cipherbox.errors import VaultError
from cipherbox.storage.repository import VaultRepository


def resolve_vault_key(vault_path: Path) -> bytes | None:
    """Resolve the decryption key for an encrypted vault.

    Resolution order:
      1. OS keyring entry for ``vault_path`` (derived key, no prompt).
      2. ``VAULT_PASSWORD`` environment variable (derive via Argon2id).
      3. Hidden ``getpass`` prompt (derive via Argon2id).

    Returns the derived key bytes, or ``None`` if the vault is not
    encrypted or no key could be obtained.
    """
    try:
        meta = load_vault_crypto(vault_path)
    except FileNotFoundError:
        # Vault not initialized yet; plaintext repository.
        return None

    if not meta.get("encrypted"):
        return None

    salt = base64.b64decode(meta["salt"])
    params = kdf_params_from_dict(meta["kdf_params"])

    # 1. OS keyring: derived key cached previously.
    store = KeyringStore()
    cached_key = store.get(vault_path)
    if cached_key is not None:
        return cached_key

    # 2. Environment variable.
    env_password = os.environ.get("VAULT_PASSWORD")
    if env_password:
        try:
            return derive_key(env_password, salt, params)
        except Exception:  # noqa: BLE001,S110 - wrong env password falls through
            pass

    # 3. Hidden prompt.
    password = prompt_password()
    mgr = VaultKeyManager()
    try:
        return mgr.unlock(password, salt, params)
    except Exception as exc:
        raise VaultError(f"failed to unlock vault: {exc}") from exc


def unlock_repo(vault_path: Path):
    """Open a repository at ``vault_path``, resolving its decryption key.

    Plaintext vaults return an unlocked repository with ``key=None``.
    Encrypted vaults resolve the key via :func:`resolve_vault_key`.
    """
    repo = VaultRepository(vault_path)

    try:
        meta = load_vault_crypto(vault_path)
    except FileNotFoundError:
        return repo

    if not meta.get("encrypted"):
        return repo

    key = resolve_vault_key(vault_path)
    if key is None:
        raise VaultError("failed to unlock vault: no key available")
    return VaultRepository(vault_path, key=key)
