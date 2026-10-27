"""Vault configuration and path handling."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VaultConfig:
    """Resolved locations for a vault: config file and entries directory."""

    vault_dir: Path
    config_file: Path

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
