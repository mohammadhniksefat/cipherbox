"""End-to-end import/export and portability verification."""

import json

from cipherbox.__main__ import main


def _seed_plaintext_vault(tmp_path):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    return vault_dir


def _add_entries(vault_dir):
    main(
        [
            "add",
            "--path",
            str(vault_dir),
            "--type",
            "login",
            "--title",
            "github",
            "--field",
            "username=alice",
            "--field",
            "password=secret1",
        ]
    )
    main(
        [
            "add",
            "--path",
            str(vault_dir),
            "--type",
            "env",
            "--title",
            "db-credentials",
            "--field",
            "DB_HOST=localhost",
            "--field",
            "DB_PASSWORD=secret2",
        ]
    )


def test_e2e_export_import_round_trip_preserves_fields(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    _add_entries(vault_dir)
    export_file = tmp_path / "export.json"

    code = main(
        [
            "export",
            "--path",
            str(vault_dir),
            "--output",
            str(export_file),
        ]
    )
    assert code == 0

    fresh = tmp_path / "fresh-vault"
    assert main(["init", "--path", str(fresh), "--confirm"]) == 0

    code = main(["import", "--path", str(fresh), str(export_file), "--policy", "skip"])
    assert code == 0
    capsys.readouterr()  # clear import banner before reading list output

    # Preserved fields: the re-imported vault should have both entries with
    # their supported fields intact (schema is plaintext here).
    out = main(["list", "--path", str(fresh), "--output", "json", "--reveal"])
    assert out == 0
    data = json.loads(capsys.readouterr().out)
    titles = {e["title"] for e in data}
    assert titles == {"github", "db-credentials"}
    github = next(e for e in data if e["title"] == "github")
    assert github["fields"]["username"] == "alice"
    assert github["fields"]["password"] == "secret1"
    db = next(e for e in data if e["title"] == "db-credentials")
    assert db["fields"]["DB_HOST"] == "localhost"


def test_e2e_env_export_only_project_tagged(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    _add_entries(vault_dir)
    output = tmp_path / ".env"

    code = main(
        [
            "env",
            "export",
            "no-such-project",
            "--path",
            str(vault_dir),
            "--output",
            str(output),
        ]
    )
    assert code == 0
    assert output.read_text(encoding="utf-8") == ""


def test_e2e_export_prints_plaintext_warning(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    export_file = tmp_path / "export.json"

    code = main(["export", "--path", str(vault_dir), "--output", str(export_file)])
    assert code == 0
    err = capsys.readouterr().err
    assert "plaintext" in err.lower()
