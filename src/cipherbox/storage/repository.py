"""JSON file storage repository for vault entries.

When constructed with a ``key`` (derived from the master password), entry
files are stored as AES-GCM authenticated encryption envelopes. Without
a key, entry files are stored in plaintext (backward compatible with
Phase 1 prototypes).
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from cipherbox.config.paths import VaultConfig, save_config
from cipherbox.crypto.aead import (
    ENVELOPE_FORMAT,
    decrypt_envelope,
    encrypt_envelope,
)
from cipherbox.crypto.aead import (
    DecryptionError as CryptoDecryptionError,
)
from cipherbox.domain.entry import Entry, entry_from_dict, entry_to_dict, validate_entry
from cipherbox.errors import (
    ConflictError,
    DecryptionError,
    DuplicateIdError,
    MalformedFileError,
    MissingEntryError,
    VaultError,
)

CONFIG_FILE_NAME = "config.json"
ENTRIES_DIR_NAME = "entries"

ENVELOPE_MARKER = ENVELOPE_FORMAT


def _now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class VaultRepository:
    """File-based repository: one JSON file per entry under <vault>/entries/.

    If ``key`` is provided, entries are encrypted at rest with AES-GCM and
    the key is held only in memory for the lifetime of this repository.
    """

    def __init__(self, vault_path: str | Path, key: bytes | None = None) -> None:
        self.vault_path = Path(vault_path)
        self.entries_dir = self.vault_path / ENTRIES_DIR_NAME
        self.config_file = self.vault_path / CONFIG_FILE_NAME
        self.key = key

    def _entry_path(self, entry_id: str) -> Path:
        return self.entries_dir / f"{entry_id}.json"

    def init(self, confirm: bool = False) -> VaultConfig:
        """Initialize the vault directory, config, and entries subdirectory.

        Refuses to overwrite an existing vault unless confirm is True.
        Writes encryption metadata (random salt + KDF params) when a key
        is bound to this repository.
        """
        if self.vault_path.exists() and not confirm:
            raise VaultError(
                f"vault already exists at {self.vault_path}; pass --confirm to overwrite",
                exit_code=1,
            )
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        config = VaultConfig(vault_dir=self.vault_path, config_file=self.config_file)
        save_config(config)
        if self.key is not None:
            import os

            from cipherbox.crypto.kdf import default_kdf_params

            salt = os.urandom(16)
            params = default_kdf_params()
            meta = {
                "encrypted": True,
                "kdf": "argon2id",
                "kdf_params": {
                    "time_cost": params.time_cost,
                    "memory_cost": params.memory_cost,
                    "parallelism": params.parallelism,
                    "hash_len": params.hash_len,
                },
                "salt": base64.b64encode(salt).decode("ascii"),
            }
            existing = {}
            if self.config_file.exists():
                import json as _json

                existing = _json.loads(self.config_file.read_text(encoding="utf-8"))
            existing.update(meta)
            self.config_file.write_text(
                _json.dumps(existing, indent=2), encoding="utf-8"
            )
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
        """Load an entry, redacting secret field values by default.

        Field keys are always preserved so callers know which fields exist;
        only the values are redacted.
        """
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
                fields={key: "" for key in entry.fields},
            )
        return entry

    def edit(self, entry_id: str, updates: dict) -> Entry:
        """Update an entry, preserving id and created_at; refresh updated_at."""
        existing = self.get(entry_id)
        merged = existing.to_dict()
        merged.update(updates)
        # Deep-merge the fields map so untouched fields are preserved.
        if "fields" in updates:
            merged_fields = dict(existing.fields or {})
            merged_fields.update(updates["fields"])
            merged["fields"] = merged_fields
        # id and created_at are immutable through edit; refresh updated_at.
        merged["id"] = existing.id
        merged["created_at"] = existing.created_at
        merged["updated_at"] = _now_utc()
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
        """Load all valid entries in the vault.

        Every file is read from disk on each call (no stale in-memory
        copy across CLI invocations). Malformed files are skipped;
        DecryptionError (wrong key / locked vault) propagates so a
        locked encrypted vault never silently returns an empty list.
        Raises ConflictError if two files resolve to the same entry ID
        (a synchronization conflict) — neither copy is silently dropped.
        """
        by_id: dict[str, tuple[Entry, Path]] = {}
        entries: list[Entry] = []
        if not self.entries_dir.exists():
            return entries
        for path in sorted(self.entries_dir.glob("*.json")):
            try:
                entry = self._read_entry_file(path)
            except MalformedFileError:
                # Skip malformed files in listing; they are reported separately.
                continue
            existing = by_id.get(entry.id)
            if existing is not None:
                _other_entry, other_path = existing
                raise ConflictError(
                    f"entry id {entry.id!r} exists in {path} and {other_path}; "
                    "conflicting copies preserved for manual recovery"
                )
            by_id[entry.id] = (entry, path)
            entries.append(entry)
        return entries

    def detect_conflicts(self) -> list[dict[str, str]]:
        """Report duplicate entry IDs across files without raising.

        Returns a list of ``{"id", "file1", "file2"}`` dicts, one per
        conflicting pair. Used by recovery tooling to surface sync
        conflicts without aborting normal operation.
        """
        by_id: dict[str, tuple[str, Path]] = {}
        conflicts: list[dict[str, str]] = []
        if not self.entries_dir.exists():
            return conflicts
        for path in sorted(self.entries_dir.glob("*.json")):
            try:
                entry = self._read_entry_file(path)
            except (MalformedFileError, DecryptionError):
                # Skip files that cannot be parsed; they are not ID conflicts.
                continue
            existing = by_id.get(entry.id)
            if existing is not None:
                _, other_path = existing
                conflicts.append(
                    {"id": entry.id, "file1": str(other_path), "file2": str(path)}
                )
            else:
                by_id[entry.id] = (entry.id, path)
        return conflicts

    def _write_entry_file(self, path: Path, entry: Entry) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(entry_to_dict(entry), indent=2).encode("utf-8")
        if self.key is not None:
            envelope = encrypt_envelope(payload, self.key, b"cipherbox-entry-envelope")
            payload = json.dumps(envelope, indent=2).encode("utf-8")
        # Atomic write: temp file in same dir, then replace.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
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
            raw = path.read_bytes()
            data = json.loads(raw.decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MalformedFileError(f"entry {path.stem} is malformed: {exc}") from exc
        if isinstance(data, dict) and data.get("format") == ENVELOPE_MARKER:
            if self.key is None:
                raise DecryptionError(
                    f"entry {path.stem} is encrypted; vault is locked"
                )
            try:
                plaintext = decrypt_envelope(data, self.key)
            except CryptoDecryptionError as exc:
                raise DecryptionError(
                    f"entry {path.stem} failed authentication: {exc}"
                ) from exc
            data = json.loads(plaintext.decode("utf-8"))
        return entry_from_dict(data)
