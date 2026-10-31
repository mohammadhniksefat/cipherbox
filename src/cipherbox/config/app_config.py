"""App-level key-value configuration for cipherbox.

Separate from per-vault ``config.json`` (which lives inside each vault
directory and holds encryption metadata). App config lives outside any
vault and stores application-wide settings such as the default vault
path.

Config file location:

- Windows: ``%LOCALAPPDATA%/cipherbox/app-config.json``
- macOS/Linux: ``$XDG_CONFIG_HOME/cipherbox/app-config.json`` or
  ``~/.config/cipherbox/app-config.json``

Missing or unreadable config file is treated as an empty config.
Writes are atomic (temp file in the same directory, then replace).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    """Return the platform-appropriate cipherbox config directory."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "cipherbox"


def _app_config_file() -> Path:
    """Return the path to the app config file."""
    return _config_dir() / "app-config.json"


class AppConfig:
    """In-memory key-value config loaded from the app config file.

    Writes are persisted immediately to disk. Missing config file is
    treated as an empty config; corrupt JSON raises ValueError.
    """

    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or _app_config_file()
        self._data: dict[str, Any] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        try:
            raw = self.config_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._data = {}
            self._loaded = True
            return
        except OSError as exc:
            raise ValueError(
                f"cannot read config file {self.config_file}: {exc}"
            ) from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"config file {self.config_file} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise TypeError(
                f"config file {self.config_file} must contain a JSON object"
            )
        self._data = data
        self._loaded = True

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for ``key``, or ``default`` if missing."""
        self._load()
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set ``key`` to ``value`` and persist to disk."""
        self._load()
        self._data[key] = value
        self._persist()

    def unset(self, key: str) -> None:
        """Remove ``key`` from config. Missing key is not an error."""
        self._load()
        self._data.pop(key, None)
        self._persist()

    def _persist(self) -> None:
        """Atomically write current data to the config file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._data, indent=2).encode("utf-8")
        import tempfile

        fd, tmp_name = tempfile.mkstemp(dir=self.config_file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.config_file)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def load_app_config() -> AppConfig:
    """Load the app config from its default location.

    Reads and validates the config file eagerly; corrupt JSON raises
    ValueError. Missing file is treated as an empty config.
    """
    cfg = AppConfig()
    cfg._load()
    return cfg


def save_app_config(data: dict[str, Any]) -> None:
    """Replace the entire app config with ``data`` and persist."""
    cfg = AppConfig()
    cfg._data = dict(data)
    cfg._loaded = True
    cfg._persist()
