"""Tests for vault key management: unlock, lock, zeroize, password prompt."""

import pytest

from cipherbox.crypto.kdf import default_kdf_params
from cipherbox.crypto.vault import (
    VaultKeyManager,
    load_vault_crypto,
    prompt_password,
    save_vault_crypto,
    zeroize_key,
)


def test_key_manager_unlock_hold_then_lock():
    mgr = VaultKeyManager()
    assert mgr.key is None
    key = mgr.unlock("pw", b"salt1234567890ab", default_kdf_params())
    assert mgr.key == key
    assert len(key) == 32
    mgr.lock()
    assert mgr.key is None


def test_key_manager_unlock_twice_replaces_key():
    mgr = VaultKeyManager()
    key1 = mgr.unlock("pw-a", b"salt1234567890ab", default_kdf_params())
    key2 = mgr.unlock("pw-b", b"salt1234567890ab", default_kdf_params())
    assert mgr.key == key2
    assert key1 != key2


def test_zeroize_key_overwrites_buffer():
    buf = bytearray(b"sensitive-key-material")
    zeroize_key(buf)
    assert buf == bytearray(len(buf))


def test_prompt_password_reads_hidden(monkeypatch):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "s3cret")
    assert prompt_password() == "s3cret"


def test_prompt_password_passes_prompt_through(monkeypatch):
    captured = {}

    def fake_getpass(prompt="Enter master password: "):
        captured["prompt"] = prompt
        return "pw"

    monkeypatch.setattr("getpass.getpass", fake_getpass)
    assert prompt_password(prompt="Vault unlock: ") == "pw"
    assert captured["prompt"] == "Vault unlock: "


def test_load_and_save_vault_crypto_round_trip(tmp_path):
    meta = {
        "encrypted": True,
        "kdf": "argon2id",
        "kdf_params": {
            "time_cost": 3,
            "memory_cost": 65536,
            "parallelism": 4,
            "hash_len": 32,
        },
        "salt": "c2FsdDEyMzQ1Njc4OWFi",
    }
    save_vault_crypto(tmp_path, meta)
    loaded = load_vault_crypto(tmp_path)
    assert loaded == meta


def test_load_vault_crypto_missing_config_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_vault_crypto(tmp_path)
