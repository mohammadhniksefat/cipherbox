"""Tests for the `vault backup` and `vault restore` CLI commands."""

import argparse
import json

from cipherbox.__main__ import main


def _args(**kwargs):
    defaults = {
        "path": None,
        "backup_command": None,
        "backup_dir": None,
        "backup_id": None,
        "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _seed_plaintext_vault(tmp_path):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    return vault_dir


def test_backup_create_and_list(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    backup_dir = tmp_path / "backups"

    code = main(
        ["backup", "create", "--path", str(vault_dir), "--backup-dir", str(backup_dir)]
    )
    assert code == 0
    backup_id = capsys.readouterr().out.strip()
    assert backup_id

    code = main(
        ["backup", "list", "--path", str(vault_dir), "--backup-dir", str(backup_dir)]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert backup_id in out


def test_backup_restore_into_empty_vault(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    backup_dir = tmp_path / "backups"

    code = main(
        ["backup", "create", "--path", str(vault_dir), "--backup-dir", str(backup_dir)]
    )
    assert code == 0
    backup_id = capsys.readouterr().out.strip()

    # restore into a fresh vault
    fresh = tmp_path / "fresh"
    code = main(
        [
            "backup",
            "restore",
            backup_id,
            "--path",
            str(fresh),
            "--backup-dir",
            str(backup_dir),
        ]
    )
    assert code == 0


def test_backup_restore_dry_run_writes_nothing(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    capsys.readouterr()  # clear init banner
    backup_dir = tmp_path / "backups"

    code = main(
        ["backup", "create", "--path", str(vault_dir), "--backup-dir", str(backup_dir)]
    )
    assert code == 0
    backup_id = capsys.readouterr().out.strip()

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    code = main(
        [
            "backup",
            "restore",
            backup_id,
            "--path",
            str(fresh),
            "--backup-dir",
            str(backup_dir),
            "--dry-run",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Would restore" in out


def test_backup_restore_invalid_backup_fails(tmp_path, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)
    backup_dir = tmp_path / "backups"

    code = main(
        ["backup", "restore", "no-such-id", "--path", str(vault_dir), "--backup-dir", str(backup_dir)]
    )
    assert code != 0
    err = capsys.readouterr().err
    assert "error" in err.lower()
