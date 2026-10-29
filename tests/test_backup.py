"""Tests for the backup service."""

import json
from pathlib import Path

from cipherbox.backup import (
    create_backup,
    default_backup_dir,
    list_backups,
    restore_backup,
    validate_backup,
)
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _seed_vault(tmp_path, count=2):
    vault_dir = tmp_path / "vault"
    repo = VaultRepository(vault_dir)
    vault_dir.mkdir(parents=True, exist_ok=True)
    (vault_dir / "entries").mkdir(parents=True, exist_ok=True)
    (vault_dir / "config.json").write_text(
        json.dumps({"vault_dir": str(vault_dir)}), encoding="utf-8"
    )
    for i in range(count):
        repo.add(
            Entry(
                id=f"id-{i}",
                schema_version=1,
                type="login",
                title=f"entry-{i}",
                tags=[],
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                fields={"username": "alice"},
            )
        )
    return vault_dir, repo


def test_create_backup_writes_config_and_entries_outside_vault(tmp_path):
    vault_dir, _ = _seed_vault(tmp_path)
    backup_dir = tmp_path / "backups"

    backup_id = create_backup(vault_dir, backup_dir=backup_dir)

    backup_root = backup_dir / backup_id
    assert backup_root.is_dir()
    assert (backup_root / "config.json").exists()
    assert (backup_root / "backup.json").exists()
    entries = list((backup_root / "entries").glob("*.json"))
    assert len(entries) == 2
    # outside the active vault
    assert backup_dir != vault_dir


def test_create_backup_returns_id_and_records_metadata(tmp_path):
    vault_dir, _ = _seed_vault(tmp_path, count=3)
    backup_dir = tmp_path / "backups"

    backup_id = create_backup(vault_dir, backup_dir=backup_dir)
    meta = json.loads((backup_dir / backup_id / "backup.json").read_text(encoding="utf-8"))
    assert meta["id"] == backup_id
    assert meta["entry_count"] == 3
    assert meta["vault_dir"] == str(vault_dir)
    assert "created_at" in meta


def test_list_backups_lists_created_backups(tmp_path):
    vault_dir, _ = _seed_vault(tmp_path)
    backup_dir = tmp_path / "backups"

    bid1 = create_backup(vault_dir, backup_dir=backup_dir)
    bid2 = create_backup(vault_dir, backup_dir=backup_dir)

    listed = list_backups(backup_dir=backup_dir)
    ids = [b["id"] for b in listed]
    assert bid1 in ids and bid2 in ids
    # newest first
    assert ids.index(bid2) < ids.index(bid1)


def test_validate_backup_true_for_good_backup(tmp_path):
    vault_dir, _ = _seed_vault(tmp_path)
    backup_dir = tmp_path / "backups"
    backup_id = create_backup(vault_dir, backup_dir=backup_dir)
    assert validate_backup(backup_id, backup_dir=backup_dir) is True


def test_validate_backup_false_for_missing_backup(tmp_path):
    backup_dir = tmp_path / "backups"
    assert validate_backup("no-such-id", backup_dir=backup_dir) is False


def test_validate_backup_false_for_corrupted_backup(tmp_path):
    vault_dir, _ = _seed_vault(tmp_path)
    backup_dir = tmp_path / "backups"
    backup_id = create_backup(vault_dir, backup_dir=backup_dir)
    # corrupt an entry file
    entry_file = next((backup_dir / backup_id / "entries").glob("*.json"))
    entry_file.write_text("{not valid json", encoding="utf-8")
    assert validate_backup(backup_id, backup_dir=backup_dir) is False


def test_restore_backup_round_trip(tmp_path):
    vault_dir, _ = _seed_vault(tmp_path, count=2)
    backup_dir = tmp_path / "backups"
    backup_id = create_backup(vault_dir, backup_dir=backup_dir)

    # empty a fresh vault, then restore into it
    fresh = tmp_path / "fresh-vault"
    fresh.mkdir()
    (fresh / "entries").mkdir()
    (fresh / "config.json").write_text(json.dumps({}), encoding="utf-8")

    restore_backup(backup_id, fresh, backup_dir=backup_dir)
    repo = VaultRepository(fresh)
    ids = {e.id for e in repo.list()}
    assert ids == {"id-0", "id-1"}
    assert repo.get("id-0").title == "entry-0"


def test_restore_backup_is_non_destructive(tmp_path):
    vault_dir, _ = _seed_vault(tmp_path, count=1)
    backup_dir = tmp_path / "backups"
    backup_id = create_backup(vault_dir, backup_dir=backup_dir)

    # restore into a vault that already has an entry with the same id
    # (write the file directly to bypass repo.add's duplicate-ID check)
    entries_dir = vault_dir / "entries"
    (entries_dir / "id-0.json").write_text(
        json.dumps(
            {
                "id": "id-0",
                "schema_version": 1,
                "type": "login",
                "title": "existing",
                "tags": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "fields": {},
            }
        ),
        encoding="utf-8",
    )
    try:
        restore_backup(backup_id, vault_dir, backup_dir=backup_dir)
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected FileExistsError for non-destructive restore")


def test_restore_backup_dry_run_writes_nothing(tmp_path):
    vault_dir, repo = _seed_vault(tmp_path, count=1)
    backup_dir = tmp_path / "backups"
    backup_id = create_backup(vault_dir, backup_dir=backup_dir)

    # modify the live vault
    repo.add(
        Entry(
            id="id-9",
            schema_version=1,
            type="login",
            title="should-not-persist",
            tags=[],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            fields={},
        )
    )
    restore_backup(backup_id, vault_dir, backup_dir=backup_dir, dry_run=True)
    ids = {e.id for e in VaultRepository(vault_dir).list()}
    assert "id-9" in ids  # dry run did not overwrite
