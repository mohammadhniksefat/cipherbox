"""Tests for the `vault encrypt` command."""

import json

from cipherbox.__main__ import main
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _seed_plaintext_vault(tmp_path, password="master"):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    repo = VaultRepository(vault_dir)
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
    return vault_dir


def test_encrypt_plaintext_vault(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)

    inputs = iter(["master", "master", "y"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(inputs))
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["encrypt", "--path", str(vault_dir)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Encrypted 2 entries" in out

    # Config now has encryption metadata.
    config = json.loads((vault_dir / "config.json").read_text(encoding="utf-8"))
    assert config["encrypted"] is True
    assert config["kdf"] == "argon2id"
    assert "salt" in config

    # Every entry file is now an encrypted envelope; no plaintext on disk.
    entries_dir = vault_dir / "entries"
    for entry_file in entries_dir.glob("*.json"):
        raw = entry_file.read_text(encoding="utf-8")
        assert "github" not in raw
        assert "alice" not in raw
        assert "secret" not in raw
        assert "sk-xyz" not in raw
        assert "cipherbox-vault-enc/1" in raw


def test_encrypt_already_encrypted_vault(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)

    # Encrypt once.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["encrypt", "--path", str(vault_dir)])
    assert code == 0
    capsys.readouterr()

    # Encrypt again should refuse.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master2")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["encrypt", "--path", str(vault_dir)])
    assert code != 0
    err = capsys.readouterr().err
    assert "already encrypted" in err


def test_encrypt_uninitialized_vault(tmp_path, monkeypatch, capsys):
    vault_dir = tmp_path / "nonexistent"
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["encrypt", "--path", str(vault_dir)])
    assert code != 0
    err = capsys.readouterr().err
    assert "not initialized" in err


def test_encrypt_password_mismatch(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)

    password_prompts = iter(["master", "different"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(password_prompts))
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["encrypt", "--path", str(vault_dir)])
    assert code != 0
    err = capsys.readouterr().err
    assert "confirmation does not match" in err


def test_encrypt_then_decrypt_roundtrip(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_plaintext_vault(tmp_path)

    # Encrypt.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["encrypt", "--path", str(vault_dir)])
    assert code == 0
    capsys.readouterr()

    # Decrypt with correct password.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
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


def test_encrypt_invalidates_keyring_and_offers_restore(tmp_path, monkeypatch, capsys):
    """On encrypt, stale keyring entry is erased and user prompted to store
    the new derived key (mirrors vault password change)."""
    vault_dir = _seed_plaintext_vault(tmp_path)

    class FakeKeyring:
        def __init__(self):
            self._data = {}

        def get_password(self, service, username):
            return self._data.get(username)

        def set_password(self, service, username, password):
            self._data[username] = password

        def delete_password(self, service, username):
            self._data.pop(username, None)

    fake = FakeKeyring()
    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", fake)

    # Pre-populate the keyring with a stale derived key.
    fake._data[str(vault_dir.resolve())] = b"stale-key-bytes"

    # Password "master" x2, then "y" to store new key in keyring.
    inputs = iter(["master", "master", "y"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(inputs))
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    code = main(["encrypt", "--path", str(vault_dir)])
    assert code == 0
    capsys.readouterr()

    # Stale keyring entry is gone (erased).
    assert fake._data.get(str(vault_dir.resolve())) != b"stale-key-bytes"
    # New derived key was stored (user said "y").
    assert str(vault_dir.resolve()) in fake._data

    # New password unlocks the encrypted vault via keyring-cached key.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    code = main(["decrypt", "--path", str(vault_dir)])
    assert code == 0
