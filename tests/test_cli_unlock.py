"""Tests for hidden password prompt + unlock wiring in the CLI."""

import json

from cipherbox.__main__ import main


def _seed_encrypted(tmp_path, monkeypatch, password="master", capsys=None):
    """Seed an encrypted vault with one entry, bypassing the CLI prompt."""
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    if capsys is not None:
        capsys.readouterr()  # clear init's "Initialized vault" line
    from cipherbox.crypto.kdf import default_kdf_params, derive_key
    from cipherbox.domain.entry import Entry
    from cipherbox.storage.repository import VaultRepository

    key = derive_key(password, b"salt1234567890ab", default_kdf_params())
    repo = VaultRepository(vault_dir, key=key)
    repo.add(
        Entry(
            id="id-a",
            schema_version=1,
            type="login",
            title="github",
            tags=["dev"],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            fields={"username": "alice", "password": "secret"},
        )
    )
    from cipherbox.crypto.vault import save_vault_crypto

    save_vault_crypto(
        vault_dir,
        {
            "encrypted": True,
            "kdf": "argon2id",
            "kdf_params": {
                "time_cost": 3,
                "memory_cost": 65536,
                "parallelism": 4,
                "hash_len": 32,
            },
            "salt": "c2FsdDEyMzQ1Njc4OTBhYg==",
        },
    )
    return vault_dir


def test_list_on_encrypted_requires_password(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted(tmp_path, monkeypatch, capsys=capsys)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["fields"]["password"] == "<redacted>"


def test_wrong_password_errors(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted(tmp_path, monkeypatch, capsys=capsys)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wrong")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code != 0
    err = capsys.readouterr().err
    assert "secret" not in err.lower()
    assert "alice" not in err.lower()


def test_init_does_not_prompt_password(tmp_path, monkeypatch):
    vault_dir = tmp_path / "vault"
    prompted = []

    def fake_getpass(prompt="Enter master password: "):
        prompted.append(prompt)
        return "unused"

    monkeypatch.setattr("getpass.getpass", fake_getpass)
    code = main(["init", "--path", str(vault_dir), "--confirm"])
    assert code == 0
    assert prompted == []


def test_password_is_not_on_cli_argv(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted(tmp_path, monkeypatch, capsys=capsys)
    captured_argv = []
    import argparse

    original_parse_args = argparse.ArgumentParser.parse_args

    def capture_parse_args(self, args=None, namespace=None):
        captured_argv.append(list(args or []))
        return original_parse_args(self, args, namespace)

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", capture_parse_args)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    for argv in captured_argv:
        assert "master" not in argv
