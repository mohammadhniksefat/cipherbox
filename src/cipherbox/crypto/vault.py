"""Vault key management: unlock, lock, zeroize, and password prompt.

The derived key is held only in memory during process execution. Locking
attempts best-effort zeroization of the held key material before the
reference is dropped — no guaranteed memory erasure is claimed.
"""

from __future__ import annotations

import getpass
from pathlib import Path

from cipherbox.crypto.kdf import KDFParams, derive_key

CONFIG_FILE_NAME = "config.json"


def prompt_password(prompt: str = "Enter master password: ") -> str:
    """Read the master password through a hidden prompt.

    Never echoed to the terminal and never accepted as a normal CLI
    argument.
    """
    return getpass.getpass(prompt)


def zeroize_key(key: bytearray) -> None:
    """Best-effort overwrite of key material in a mutable buffer.

    No guaranteed memory erasure is claimed; this reduces the window in
    which the key sits in process memory.
    """
    for i in range(len(key)):
        key[i] = 0


class VaultKeyManager:
    """Holds the derived master key in memory for the lifetime of a command.

    ``unlock`` derives the key with Argon2id and retains it. ``lock``
    best-effort zeroizes and clears it. ``key`` is None when locked.
    """

    def __init__(self) -> None:
        self._key: bytes | None = None

    @property
    def key(self) -> bytes | None:
        return self._key

    def unlock(self, password: str, salt: bytes, params: KDFParams) -> bytes:
        """Derive and hold the master key in memory."""
        self._key = derive_key(password, salt, params)
        return self._key

    def lock(self) -> None:
        """Best-effort zeroize and clear the held key."""
        if self._key is not None:
            zeroize_key(bytearray(self._key))
        self._key = None


def _read_config(vault_dir: Path) -> dict:
    """Read the vault config file, returning an empty dict if absent."""
    import json

    config_file = vault_dir / CONFIG_FILE_NAME
    if not config_file.exists():
        return {}
    return json.loads(config_file.read_text(encoding="utf-8"))


def save_vault_crypto(vault_dir: Path, meta: dict) -> None:
    """Persist encryption metadata into the vault config file.

    Existing config keys (such as ``vault_dir``) are preserved; crypto
    metadata is merged on top.
    """
    import json

    config_file = vault_dir / CONFIG_FILE_NAME
    config_file.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_config(vault_dir)
    existing.update(meta)
    config_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def load_vault_crypto(vault_dir: Path) -> dict:
    """Load the full vault config (vault dir plus encryption metadata)."""
    import json

    config_file = vault_dir / CONFIG_FILE_NAME
    if not config_file.exists():
        raise FileNotFoundError(f"vault config not found: {config_file}")
    return json.loads(config_file.read_text(encoding="utf-8"))
