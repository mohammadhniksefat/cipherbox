"""Tests for the `vault decrypt` command."""

import json

from cipherbox.__main__ import main
from cipherbox.crypto.kdf import default_kdf_params, derive_key
from cipherbox.crypto.vault import save_vault_crypto
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _seed_encrypted_vault(tmp_path, password="master"):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0

    key = derive_key(password, b"salt1234567890ab", default_kdf_params())
    repo = VaultRepository(vault_dir, key=key)
    entries = [
        Entry(
            id="id-a",
            schema_version=1,
            type="login",
            title="github",
            tags=["dev"],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            fields={"username": "alice", "password": "secret"},
        ),
        Entry(
            id="id-b",
            schema_version=1,
            type="api-key",
            title="openai",
            tags=["dev"],
            created_at="2026-01-02T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
            fields={"provider": "openai", "token": "sk-xyz"},
        ),
    ]
    for entry in entries:
        repo.add(entry)
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


def test_decrypt_encrypted_vault(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path)

    # confirmation "y", then password "master"
    answers = iter(["y", "master"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    code = main(["decrypt", "--path", str(vault_dir)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Decrypted 2 entries" in out

    # Config no longer has encryption metadata.
    config = json.loads((vault_dir / "config.json").read_text(encoding="utf-8"))
    assert config.get("encrypted") is not True
    assert "kdf" not in config
    assert "salt" not in config

    # Entry files are plaintext again with original contents.
    entries_dir = vault_dir / "entries"
    for entry_file in entries_dir.glob("*.json"):
        raw = entry_file.read_text(encoding="utf-8")
        assert "cipherbox-vault-enc/1" not in raw
    data = json.loads((entries_dir / "id-a.json").read_text(encoding="utf-8"))
    assert data["title"] == "github"
    assert data["fields"]["password"] == "secret"
    assert data["fields"]["username"] == "alice"


def test_decrypt_plaintext_vault_refused(tmp_path, monkeypatch, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0

    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["decrypt", "--path", str(vault_dir)])
    assert code != 0
    err = capsys.readouterr().err
    assert "not encrypted" in err


def test_decrypt_uninitialized_vault(tmp_path, monkeypatch, capsys):
    vault_dir = tmp_path / "nonexistent"
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["decrypt", "--path", str(vault_dir)])
    assert code != 0
    err = capsys.readouterr().err
    assert "not initialized" in err


def test_decrypt_wrong_password(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path)

    answers = iter(["y", "wrong"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    code = main(["decrypt", "--path", str(vault_dir)])
    assert code != 0
    err = capsys.readouterr().err
    assert "authentication failed" in err
