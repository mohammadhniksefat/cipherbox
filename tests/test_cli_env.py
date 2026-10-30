"""Tests for the `vault env export` CLI command."""

import json

from cipherbox.__main__ import main


def _seed_plaintext_vault(tmp_path):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    return vault_dir


def _write_entries_with_tags(vault_dir):
    entries_dir = vault_dir / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    (vault_dir / "config.json").write_text(
        json.dumps({"vault_dir": str(vault_dir)}), encoding="utf-8"
    )
    db = {
        "id": "id-db",
        "schema_version": 1,
        "type": "env",
        "title": "db-credentials",
        "tags": ["my-project"],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {"DB_HOST": "localhost", "DB_PASSWORD": "secret"},
    }
    gh = {
        "id": "id-gh",
        "schema_version": 1,
        "type": "login",
        "title": "github",
        "tags": ["my-project", "personal"],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {"token": "abc123"},
    }
    other = {
        "id": "id-other",
        "schema_version": 1,
        "type": "login",
        "title": "unrelated",
        "tags": ["other-project"],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {"token": "xyz"},
    }
    for entry in (db, gh, other):
        (entries_dir / f"{entry['id']}.json").write_text(
            json.dumps(entry), encoding="utf-8"
        )


def test_cli_env_export_only_project_tagged(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    _write_entries_with_tags(vault_dir)
    output = tmp_path / ".env"

    code = main(
        [
            "env",
            "export",
            "my-project",
            "--path",
            str(vault_dir),
            "--output",
            str(output),
        ]
    )
    assert code == 0
    contents = output.read_text(encoding="utf-8")
    assert 'DB_HOST="localhost"' in contents
    assert 'DB_PASSWORD="secret"' in contents
    assert 'TOKEN="abc123"' in contents
    # unrelated secret must not appear
    assert "xyz" not in contents


def test_cli_env_export_refuses_to_overwrite_without_confirm(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    _write_entries_with_tags(vault_dir)
    output = tmp_path / ".env"
    output.write_text("PREEXISTING=1", encoding="utf-8")

    code = main(
        [
            "env",
            "export",
            "my-project",
            "--path",
            str(vault_dir),
            "--output",
            str(output),
        ]
    )
    assert code != 0
    err = capsys.readouterr().err
    assert "error" in err.lower()


def test_cli_env_export_overwrites_with_confirm(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    _write_entries_with_tags(vault_dir)
    output = tmp_path / ".env"
    output.write_text("PREEXISTING=1", encoding="utf-8")

    code = main(
        [
            "env",
            "export",
            "my-project",
            "--path",
            str(vault_dir),
            "--output",
            str(output),
            "--confirm",
        ]
    )
    assert code == 0


def test_cli_env_export_prints_plaintext_warning(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    _write_entries_with_tags(vault_dir)
    output = tmp_path / ".env"

    code = main(
        [
            "env",
            "export",
            "my-project",
            "--path",
            str(vault_dir),
            "--output",
            str(output),
        ]
    )
    assert code == 0
    err = capsys.readouterr().err
    assert "plaintext" in err.lower()
