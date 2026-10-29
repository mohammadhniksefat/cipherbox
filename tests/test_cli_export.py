"""Tests for the `vault export` CLI command."""

import argparse

from cipherbox.__main__ import main


def _args(**kwargs):
    defaults = {
        "path": None,
        "format": "json",
        "output": None,
        "confirm": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _seed_plaintext_vault(tmp_path):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    return vault_dir


def test_cli_export_writes_json_export(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    output = tmp_path / "export.json"

    code = main(
        [
            "export",
            "--path",
            str(vault_dir),
            "--output",
            str(output),
        ]
    )
    assert code == 0
    assert output.exists()
    import json

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["format"] == "cipherbox-export/1"
    assert "entries" in data


def test_cli_export_refuses_to_overwrite_without_confirm(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    output = tmp_path / "export.json"
    output.write_text("preexisting", encoding="utf-8")

    code = main(
        [
            "export",
            "--path",
            str(vault_dir),
            "--format",
            "json",
            "--output",
            str(output),
        ]
    )
    assert code != 0
    err = capsys.readouterr().err
    assert "error" in err.lower()


def test_cli_export_overwrites_with_confirm(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    output = tmp_path / "export.json"
    output.write_text("preexisting", encoding="utf-8")

    code = main(
        [
            "export",
            "--path",
            str(vault_dir),
            "--format",
            "json",
            "--output",
            str(output),
            "--confirm",
        ]
    )
    assert code == 0


def test_cli_export_prints_plaintext_warning(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    output = tmp_path / "export.json"

    code = main(
        [
            "export",
            "--path",
            str(vault_dir),
            "--format",
            "json",
            "--output",
            str(output),
        ]
    )
    assert code == 0
    err = capsys.readouterr().err
    assert "plaintext" in err.lower()
