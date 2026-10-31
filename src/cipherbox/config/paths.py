"""Vault configuration and path handling."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VaultConfig:
    """Resolved locations for a vault: config file and entries directory.

    Encryption metadata (whether the vault is encrypted, the KDF id and
    parameters, and the random salt) lives in the config file and is
    loaded separately via :func:`load_vault_crypto`.
    """

    vault_dir: Path
    config_file: Path
    encrypted: bool = False
    kdf: str | None = None
    kdf_params: dict | None = None
    salt: str | None = None

    @property
    def entries_dir(self) -> Path:
        return self.vault_dir / "entries"


def default_vault_dir() -> Path:
    """Return the platform-appropriate default vault directory."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "cipherbox-vault"


def resolve_vault_dir(path: str | Path | None = None) -> Path:
    """Resolve the vault directory to operate on.

    Resolution order:
    1. ``path`` (the ``--path`` argument) always wins when given.
    2. Otherwise, the app config ``default-vault`` key, if set.
    3. Otherwise, fall back to ``default_vault_dir()``.
    """
    if path is not None:
        return Path(path)

    from cipherbox.config.app_config import load_app_config

    app_config = load_app_config()
    default_vault = app_config.get("default-vault")
    if default_vault:
        return Path(default_vault)

    return default_vault_dir()


def save_config(config: VaultConfig) -> None:
    """Persist a VaultConfig to its config_file as JSON."""
    config.config_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"vault_dir": str(config.vault_dir)}
    config.config_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_config(config_file: Path) -> VaultConfig:
    """Load a VaultConfig from its config_file JSON."""
    data = json.loads(config_file.read_text(encoding="utf-8"))
    vault_dir = Path(data["vault_dir"])
    return VaultConfig(vault_dir=vault_dir, config_file=config_file)
