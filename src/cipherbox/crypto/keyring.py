"""OS keyring storage for vault derived keys.

Stores the *derived* AES-256 key (never the master password) in the OS
credential store, keyed by vault path. Falls back gracefully when the
keyring backend is unavailable.
"""

from __future__ import annotations

from pathlib import Path

try:
    import keyring as _keyring_mod
except ImportError:  # pragma: no cover - keyring is optional
    _keyring_mod = None


class KeyringStore:
    """Persist and retrieve a vault's derived key in the OS keyring.

    Each vault path maps to one keyring credential. The service name is
    ``cipherbox`` and the username is the resolved vault path string.
    """

    def __init__(self, service_name: str = "cipherbox") -> None:
        self.service_name = service_name

    def _username(self, vault_path: Path) -> str:
        return str(vault_path.resolve())

    def get(self, vault_path: Path) -> bytes | None:
        """Return the stored derived key for ``vault_path``, or None."""
        if _keyring_mod is None:
            return None
        value = _keyring_mod.get_password(self.service_name, self._username(vault_path))
        if value is None:
            return None
        return value.encode("latin-1")

    def store(self, vault_path: Path, key: bytes) -> None:
        """Store the derived key for ``vault_path`` in the keyring."""
        if _keyring_mod is None:
            return
        _keyring_mod.set_password(
            self.service_name, self._username(vault_path), key.decode("latin-1")
        )

    def erase(self, vault_path: Path) -> None:
        """Remove the stored key for ``vault_path``. Missing entry is OK."""
        if _keyring_mod is None:
            return
        try:
            _keyring_mod.delete_password(self.service_name, self._username(vault_path))
        except Exception:  # noqa: BLE001,S110 - missing entry is not an error
            pass
