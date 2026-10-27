"""JSON file storage repository for vault entries."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from cipherbox.config.paths import VaultConfig, save_config
from cipherbox.domain.entry import Entry, entry_from_dict, entry_to_dict, validate_entry
from cipherbox.errors import (
    DuplicateIdError,
    MalformedFileError,
    MissingEntryError,
    VaultError,
)

CONFIG_FILE_NAME = "config.json"
ENTRIES_DIR_NAME = "entries"


class VaultRepository:
    """File-based repository: one JSON file per entry under <vault>/entries/."""

    def __init__(self, vault_path: str | Path) -> None:
        self.vault_path = Path(vault_path)
        self.entries_dir = self.vault_path / ENTRIES_DIR_NAME
        self.config_file = self.vault_path / CONFIG_FILE_NAME

    def _entry_path(self, entry_id: str) -> Path:
        return self.entries_dir / f"{entry_id}.json"

    def init(self, confirm: bool = False) -> VaultConfig:
        """Initialize the vault directory, config, and entries subdirectory.

        Refuses to overwrite an existing vault unless confirm is True.
        """
        if self.vault_path.exists() and not confirm:
            raise VaultError(
                f"vault already exists at {self.vault_path}; pass --confirm to overwrite",
                exit_code=1,
            )
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        config = VaultConfig(vault_dir=self.vault_path, config_file=self.config_file)
        save_config(config)
        return config

    def add(self, entry: Entry) -> None:
        """Add a new entry, rejecting duplicate IDs."""
        validate_entry(entry)
        path = self._entry_path(entry.id)
        if path.exists():
            raise DuplicateIdError(f"entry {entry.id} already exists")
        self._write_entry_file(path, entry)

    def get(self, entry_id: str) -> Entry:
        """Load and validate an entry by ID."""
        path = self._entry_path(entry_id)
        return self._read_entry_file(path)

    def show(self, entry_id: str, redact: bool = True) -> Entry:
        """Load an entry, redacting secret fields by default."""
        entry = self.get(entry_id)
        if redact:
            return Entry(
                id=entry.id,
                schema_version=entry.schema_version,
                type=entry.type,
                title=entry.title,
                tags=list(entry.tags),
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                fields={},
            )
        return entry

    def edit(self, entry_id: str, updates: dict) -> Entry:
        """Update an entry, preserving id and created_at; refresh updated_at."""
        existing = self.get(entry_id)
        merged = existing.to_dict()
        merged.update(updates)
        # id and created_at are immutable through edit.
        merged["id"] = existing.id
        merged["created_at"] = existing.created_at
        entry = entry_from_dict(merged)
        self._write_entry_file(self._entry_path(entry_id), entry)
        return entry

    def delete(self, entry_id: str, confirm: bool = False) -> None:
        """Delete an entry's file. Only that entry's file is removed."""
        path = self._entry_path(entry_id)
        if not path.exists():
            raise MissingEntryError(f"entry {entry_id} not found")
        path.unlink()

    def list(self) -> list[Entry]:
        """Load all valid entries in the vault."""
        entries: list[Entry] = []
        if not self.entries_dir.exists():
            return entries
        for path in sorted(self.entries_dir.glob("*.json")):
            try:
                entries.append(self._read_entry_file(path))
            except VaultError:
                # Skip malformed files in listing; they are reported separately.
                continue
        return entries

    def _write_entry_file(self, path: Path, entry: Entry) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(entry_to_dict(entry), indent=2)
        # Atomic write: temp file in same dir, then replace.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _read_entry_file(self, path: Path) -> Entry:
        if not path.exists():
            raise MissingEntryError(f"entry {path.stem} not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MalformedFileError(
                f"entry {path.stem} is malformed: {exc}"
            ) from exc
        return entry_from_dict(data)
