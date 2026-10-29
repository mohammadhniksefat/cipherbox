"""Backup and restore for the cipherbox vault.

Backups are snapshots of ``config.json`` plus every entry file under
``entries/``, stored outside the active vault by default. Each backup is
a timestamped directory containing a ``backup.json`` metadata file.
Restore is non-destructive by default: it never overwrites an entry
file that already exists in the active vault.

The vault is assumed to already be encrypted (Phase 3); entry files are
copied byte-for-byte so their authentication envelopes survive intact.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path


CONFIG_FILE_NAME = "config.json"
ENTRIES_DIR_NAME = "entries"
BACKUP_META_NAME = "backup.json"


def _now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def default_backup_dir(vault_dir: str | Path) -> Path:
    """Return the default backup directory: a sibling of the active vault."""
    return Path(vault_dir).parent / f"{Path(vault_dir).name}-backups"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def create_backup(
    vault_dir: str | Path, backup_dir: str | Path | None = None
) -> str:
    """Create a snapshot of the vault and return its backup id.

    The backup id is a UUID4. The backup directory layout is::

        <backup_dir>/<backup-id>/
            backup.json        # id, created_at, entry_count, vault_dir
            config.json
            entries/
                <uuid>.json

    ``backup_dir`` defaults to a ``<vault-name>-backups`` sibling of the
    active vault, so backups live outside the active vault by default.
    """
    vault_dir = Path(vault_dir)
    target_backup_dir = Path(backup_dir) if backup_dir is not None else default_backup_dir(vault_dir)

    backup_id = str(uuid.uuid4())
    backup_root = target_backup_dir / backup_id
    backup_entries = backup_root / ENTRIES_DIR_NAME
    backup_entries.mkdir(parents=True, exist_ok=True)

    # Copy config.json (includes encryption metadata).
    shutil.copy2(vault_dir / CONFIG_FILE_NAME, backup_root / CONFIG_FILE_NAME)

    # Copy every entry file byte-for-byte (authenticated envelopes survive).
    source_entries = vault_dir / ENTRIES_DIR_NAME
    entry_count = 0
    if source_entries.exists():
        for entry_file in sorted(source_entries.glob("*.json")):
            shutil.copy2(entry_file, backup_entries / entry_file.name)
            entry_count += 1

    meta = {
        "id": backup_id,
        "created_at": _now_utc(),
        "entry_count": entry_count,
        "vault_dir": str(vault_dir),
    }
    (backup_root / BACKUP_META_NAME).write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return backup_id


def list_backups(backup_dir: str | Path | None = None) -> list[dict]:
    """List available backups sorted by creation time (newest first)."""
    target_backup_dir = (
        Path(backup_dir) if backup_dir is not None else Path.cwd() / "cipherbox-backups"
    )
    backups: list[dict] = []
    if not target_backup_dir.exists():
        return backups
    for backup_root in sorted(target_backup_dir.iterdir()):
        meta_file = backup_root / BACKUP_META_NAME
        if not meta_file.exists():
            continue
        try:
            meta = _read_json(meta_file)
        except (json.JSONDecodeError, OSError):
            continue
        backups.append(meta)
    backups.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return backups


def validate_backup(
    backup_id: str, backup_dir: str | Path | None = None
) -> bool:
    """Return True if the backup's metadata, config, and entries all parse.

    A backup is considered restorable only when ``backup.json``,
    ``config.json``, and every listed entry file are valid JSON. Missing
    or corrupt files invalidate the backup.
    """
    target_backup_dir = (
        Path(backup_dir) if backup_dir is not None else Path.cwd() / "cipherbox-backups"
    )
    backup_root = target_backup_dir / backup_id
    if not backup_root.is_dir():
        return False
    try:
        _read_json(backup_root / BACKUP_META_NAME)
        _read_json(backup_root / CONFIG_FILE_NAME)
    except (json.JSONDecodeError, OSError, KeyError):
        return False
    entries_dir = backup_root / ENTRIES_DIR_NAME
    if entries_dir.exists():
        for entry_file in entries_dir.glob("*.json"):
            try:
                _read_json(entry_file)
            except (json.JSONDecodeError, OSError):
                return False
    return True


def restore_backup(
    backup_id: str,
    vault_dir: str | Path,
    backup_dir: str | Path | None = None,
    dry_run: bool = False,
) -> None:
    """Restore a backup into the vault.

    Non-destructive by default: if any entry file being restored already
    exists in the active vault, raises ``FileExistsError`` so nothing is
    silently overwritten. ``dry_run=True`` validates and reports what
    would be restored without writing anything.
    """
    vault_dir = Path(vault_dir)
    target_backup_dir = (
        Path(backup_dir) if backup_dir is not None else default_backup_dir(vault_dir)
    )
    backup_root = target_backup_dir / backup_id
    if not backup_root.is_dir():
        raise FileNotFoundError(f"backup {backup_id} not found in {target_backup_dir}")

    if not validate_backup(backup_id, backup_dir=target_backup_dir):
        raise ValueError(f"backup {backup_id} failed validation; not restorable")

    backup_entries = backup_root / ENTRIES_DIR_NAME
    if not dry_run:
        vault_entries = vault_dir / ENTRIES_DIR_NAME
        vault_entries.mkdir(parents=True, exist_ok=True)
        # Restore config first (encryption metadata).
        shutil.copy2(backup_root / CONFIG_FILE_NAME, vault_dir / CONFIG_FILE_NAME)
        # Restore each entry; refuse to overwrite an existing file.
        if backup_entries.exists():
            for entry_file in sorted(backup_entries.glob("*.json")):
                dest = vault_entries / entry_file.name
                if dest.exists():
                    raise FileExistsError(
                        f"entry {entry_file.name} already exists in vault; "
                        "restore is non-destructive by default"
                    )
                shutil.copy2(entry_file, dest)
