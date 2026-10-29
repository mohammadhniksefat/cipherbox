"""Tests for the import/export service."""

import json

import pytest

from cipherbox.domain.entry import Entry
from cipherbox.errors import EXIT_ERROR
from cipherbox.import_export import (
    EXPORT_FORMAT,
    ExportError,
    ImportError,
    ImportPolicy,
    export_entries,
    import_entries,
)
from cipherbox.storage.repository import VaultRepository


def _make_entry(entry_id: str, title: str) -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type="login",
        title=title,
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        fields={"username": "alice"},
    )


def _seed_vault(tmp_path, entries):
    vault_dir = tmp_path / "vault"
    repo = VaultRepository(vault_dir)
    repo.init(confirm=True)
    for entry in entries:
        repo.add(entry)
    return vault_dir, repo


def _export_dict(entry_id: str, title: str) -> dict:
    return {
        "id": entry_id,
        "schema_version": 1,
        "type": "login",
        "title": title,
        "tags": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {"username": "alice"},
    }


# --- export_entries ---


def test_export_entries_writes_documented_schema(tmp_path):
    vault_dir, repo = _seed_vault(tmp_path, [_make_entry("id-1", "first")])
    output = tmp_path / "export.json"

    result = export_entries(repo, output)

    assert result == str(output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["format"] == EXPORT_FORMAT
    assert "exported_at" in data
    assert data["source_vault"] == str(vault_dir)
    assert len(data["entries"]) == 1
    assert data["entries"][0]["id"] == "id-1"
    assert data["entries"][0]["title"] == "first"


def test_export_entries_round_trips_through_import(tmp_path):
    _vault_dir, repo = _seed_vault(
        tmp_path, [_make_entry("id-1", "first"), _make_entry("id-2", "second")]
    )
    output = tmp_path / "export.json"
    export_entries(repo, output)

    fresh = tmp_path / "fresh"
    fresh_repo = VaultRepository(fresh)
    fresh_repo.init(confirm=True)
    report = import_entries(fresh_repo, output, policy=ImportPolicy("skip"))
    assert report.imported == ["id-1", "id-2"]
    assert {e.id for e in fresh_repo.list()} == {"id-1", "id-2"}
    assert fresh_repo.get("id-1").title == "first"
    assert fresh_repo.get("id-2").title == "second"


def test_export_entries_refuses_to_overwrite(tmp_path):
    _vault_dir, repo = _seed_vault(tmp_path, [_make_entry("id-1", "first")])
    output = tmp_path / "export.json"
    export_entries(repo, output)
    output.write_text("preexisting", encoding="utf-8")

    with pytest.raises(FileExistsError):
        export_entries(repo, output)


def test_export_entries_overwrites_when_overwrite_true(tmp_path):
    _vault_dir, repo = _seed_vault(tmp_path, [_make_entry("id-1", "first")])
    output = tmp_path / "export.json"
    export_entries(repo, output)
    export_entries(repo, output, overwrite=True)
    assert output.exists()


# --- import_entries: validation-first ---


def test_import_invalid_entry_does_not_partially_modify_vault(tmp_path):
    _vault_dir, repo = _seed_vault(tmp_path, [_make_entry("keep", "keep")])
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "format": EXPORT_FORMAT,
                "entries": [
                    _export_dict("good", "good"),
                    {
                        "id": "bad",
                        "schema_version": 999,
                        "type": "login",
                        "title": "bad",
                        "tags": [],
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                        "fields": {},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ImportError):
        import_entries(repo, bad, policy=ImportPolicy("skip"))

    ids = {e.id for e in repo.list()}
    assert ids == {"keep"}  # nothing partially written


def test_import_malformed_json_raises(tmp_path):
    _vault_dir, repo = _seed_vault(tmp_path, [])
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ImportError):
        import_entries(repo, bad, policy=ImportPolicy("skip"))


# --- import_entries: collision policies ---


def test_import_skip_skips_existing_ids(tmp_path):
    vault_dir, repo = _seed_vault(tmp_path, [_make_entry("id-1", "existing")])
    output = tmp_path / "export.json"
    # Build an export with id-1 (different title) and id-2 (new).
    export_data = {
        "format": EXPORT_FORMAT,
        "exported_at": "2026-01-01T00:00:00Z",
        "source_vault": str(vault_dir),
        "entries": [
            _export_dict("id-1", "different-title"),
            _export_dict("id-2", "new-entry"),
        ],
    }
    output.write_text(json.dumps(export_data), encoding="utf-8")

    report = import_entries(repo, output, policy=ImportPolicy("skip"))

    assert report.imported == ["id-2"]
    assert report.skipped == ["id-1"]
    assert repo.get("id-1").title == "existing"  # untouched
    assert repo.get("id-2").title == "new-entry"


def test_import_replace_replaces_existing_ids(tmp_path):
    vault_dir, repo = _seed_vault(tmp_path, [_make_entry("id-1", "existing")])
    output = tmp_path / "export.json"
    export_data = {
        "format": EXPORT_FORMAT,
        "exported_at": "2026-01-01T00:00:00Z",
        "source_vault": str(vault_dir),
        "entries": [_export_dict("id-1", "replaced-title")],
    }
    output.write_text(json.dumps(export_data), encoding="utf-8")

    report = import_entries(repo, output, policy=ImportPolicy("replace"))

    assert report.replaced == ["id-1"]
    assert repo.get("id-1").title == "replaced-title"


def test_import_rename_generates_new_ids_for_collisions(tmp_path):
    vault_dir, repo = _seed_vault(tmp_path, [_make_entry("id-1", "existing")])
    output = tmp_path / "export.json"
    export_data = {
        "format": EXPORT_FORMAT,
        "exported_at": "2026-01-01T00:00:00Z",
        "source_vault": str(vault_dir),
        "entries": [_export_dict("id-1", "imported-title")],
    }
    output.write_text(json.dumps(export_data), encoding="utf-8")

    report = import_entries(repo, output, policy=ImportPolicy("rename"))

    assert report.imported == []
    assert len(report.renamed) == 1
    original, new = report.renamed[0]
    assert original == "id-1"
    assert new != "id-1"
    assert repo.get(new).title == "imported-title"
    assert repo.get("id-1").title == "existing"  # original untouched


# --- import_entries: title collisions and dry-run ---


def test_import_reports_title_collisions_in_warnings(tmp_path):
    vault_dir, repo = _seed_vault(tmp_path, [_make_entry("id-keep", "shared-title")])
    output = tmp_path / "export.json"
    export_data = {
        "format": EXPORT_FORMAT,
        "exported_at": "2026-01-01T00:00:00Z",
        "source_vault": str(vault_dir),
        "entries": [_export_dict("id-new", "shared-title")],
    }
    output.write_text(json.dumps(export_data), encoding="utf-8")

    report = import_entries(repo, output, policy=ImportPolicy("skip"))

    assert report.imported == ["id-new"]
    assert report.warnings
    assert any("shared-title" in w for w in report.warnings)


def test_import_dry_run_writes_nothing(tmp_path):
    vault_dir, repo = _seed_vault(tmp_path, [_make_entry("keep", "keep")])
    output = tmp_path / "export.json"
    export_data = {
        "format": EXPORT_FORMAT,
        "exported_at": "2026-01-01T00:00:00Z",
        "source_vault": str(vault_dir),
        "entries": [_export_dict("id-new", "new-entry")],
    }
    output.write_text(json.dumps(export_data), encoding="utf-8")

    report = import_entries(repo, output, policy=ImportPolicy("skip"), dry_run=True)

    assert report.dry_run is True
    assert report.imported == ["id-new"]
    ids = {e.id for e in repo.list()}
    assert ids == {"keep"}  # nothing written


# --- error types ---


def test_error_exit_codes(tmp_path):
    assert ExportError("boom").exit_code == EXIT_ERROR
    assert ImportError("boom").exit_code == EXIT_ERROR
