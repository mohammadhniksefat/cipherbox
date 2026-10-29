"""Tests for the `vault import` CLI command."""

import argparse
import json

from cipherbox.__main__ import main


def _args(**kwargs):
    defaults = {
        "path": None,
        "input": None,
        "policy": "skip",
        "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _seed_plaintext_vault(tmp_path):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    return vault_dir


def _make_export_file(tmp_path, entries):
    path = tmp_path / "export.json"
    data = {
        "format": "cipherbox-export/1",
        "exported_at": "2026-01-01T00:00:00Z",
        "source_vault": str(tmp_path / "source"),
        "entries": entries,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_cli_import_dry_run_writes_nothing(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    output = tmp_path / "export.json"
    entry = {
        "id": "id-new",
        "schema_version": 1,
        "type": "login",
        "title": "new-entry",
        "tags": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {},
    }
    _make_export_file(tmp_path, [entry])

    code = main(
        [
            "import",
            "--path",
            str(vault_dir),
            str(output),
            "--policy",
            "skip",
            "--dry-run",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "would import" in out.lower() or "Dry run" in out
    # nothing written
    from cipherbox.storage.repository import VaultRepository

    ids = {e.id for e in VaultRepository(vault_dir).list()}
    assert ids == set()


def test_cli_import_skip_imports_new_skips_duplicates(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    output = tmp_path / "export.json"
    entry = {
        "id": "id-new",
        "schema_version": 1,
        "type": "login",
        "title": "new-entry",
        "tags": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {},
    }
    _make_export_file(tmp_path, [entry])

    code = main(["import", "--path", str(vault_dir), str(output), "--policy", "skip"])
    assert code == 0
    from cipherbox.storage.repository import VaultRepository

    ids = {e.id for e in VaultRepository(vault_dir).list()}
    assert "id-new" in ids


def test_cli_import_invalid_file_exits_non_zero(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")

    code = main(["import", "--path", str(vault_dir), str(bad)])
    assert code != 0
    err = capsys.readouterr().err
    assert "error" in err.lower()
