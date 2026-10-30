"""Recovery tests: corrupted entry files and failed imports."""

import argparse
import json

from cipherbox.cli.check import check_command
from cipherbox.cli.import_ import import_command
from cipherbox.domain.entry import Entry
from cipherbox.errors import ConflictError, MissingEntryError
from cipherbox.storage.repository import VaultRepository


def _args(**kwargs) -> argparse.Namespace:
    base = {"all": True, "path": None}
    base.update(kwargs)
    return argparse.Namespace(**base)


def _make_entry(entry_id: str, title: str) -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type="login",
        title=title,
        tags=["dev"],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        fields={"username": "alice", "password": "s3cr3t-vault-1"},
    )


def test_recovery_malformed_entry_reported_as_error(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))
    # Plant a malformed entry file.
    (tmp_path / "entries" / "broken.json").write_text(
        "{not valid json", encoding="utf-8"
    )

    code = check_command(_args(path=str(tmp_path)))
    assert code != 0
    err = capsys.readouterr().err
    assert "broken" in err.lower() or "malformed" in err.lower()
    # Secret values never appear on stderr.
    assert "s3cr3t-vault-1" not in err
    # Valid entries are still usable.
    assert repo.get("id-1") is not None


def test_recovery_failed_import_leaves_vault_unchanged(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))
    before = sorted(p.name for p in (tmp_path / "entries").iterdir())

    bad = tmp_path / "bad-import.json"
    # Unknown secret type and empty title — both invalid.
    bad.write_text(
        json.dumps(
            {
                "format": "cipherbox-export/1",
                "entries": [
                    {"id": "x", "type": "nope", "title": "", "fields": {}},
                ],
            }
        ),
        encoding="utf-8",
    )

    code = import_command(
        argparse.Namespace(
            input=str(bad), path=str(tmp_path), policy="skip", dry_run=False
        )
    )
    assert code != 0
    err = capsys.readouterr().err
    # Secret values never appear on stderr.
    assert "s3cr3t-vault-1" not in err
    # Vault unchanged: no new entry files.
    after = sorted(p.name for p in (tmp_path / "entries").iterdir())
    assert before == after


def test_recovery_conflict_duplicate_ids_across_files(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))
    # Plant a second file with the same id under a different filename
    # (a synchronization conflict from an external copy).
    dup = tmp_path / "entries" / "other.json"
    dup.write_text(
        json.dumps(
            {
                "id": "id-1",
                "schema_version": 1,
                "type": "login",
                "title": "conflict",
                "tags": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
                "fields": {},
            }
        ),
        encoding="utf-8",
    )

    try:
        repo.list()
        assert False, "expected ConflictError"
    except ConflictError as exc:
        assert "id-1" in str(exc)

    conf = repo.detect_conflicts()
    assert any(c["id"] == "id-1" for c in conf)
    # Neither copy silently dropped: both files still present.
    assert (tmp_path / "entries" / "id-1.json").exists()
    assert dup.exists()
    # Secret values never on stderr.
    err = capsys.readouterr().err
    assert "s3cr3t-vault-1" not in err


def test_recovery_missing_entry_raises(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    try:
        repo.get("does-not-exist")
        assert False, "expected MissingEntryError"
    except MissingEntryError:
        pass
    err = capsys.readouterr().err
    assert "s3cr3t-vault-1" not in err
