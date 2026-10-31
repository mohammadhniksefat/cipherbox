"""Unit tests for vault keyring helpers."""

import pytest


def test_store_get_erase_round_trip(tmp_path, monkeypatch):
    from cipherbox.crypto.keyring import KeyringStore

    store = KeyringStore(service_name="test-cipherbox")

    captured = {}

    class FakeKeyring:
        @staticmethod
        def set_password(service, username, password):
            captured["value"] = password

        @staticmethod
        def get_password(service, username):
            return captured.get("value")

        @staticmethod
        def delete_password(service, username):
            captured.pop("value", None)

    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", FakeKeyring)

    vault_path = tmp_path / "my-vault"
    key = b"\x01" * 32

    assert store.store(vault_path, key) is None
    assert store.get(vault_path) == key
    assert store.erase(vault_path) is None
    assert store.get(vault_path) is None


def test_keyring_missing_returns_none(tmp_path, monkeypatch):
    from cipherbox.crypto.keyring import KeyringStore

    store = KeyringStore(service_name="test-cipherbox")

    class EmptyKeyring:
        @staticmethod
        def get_password(service, username):
            return None

    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", EmptyKeyring)

    assert store.get(tmp_path / "vault") is None


def test_keyring_backend_failure_raises(tmp_path, monkeypatch):
    from cipherbox.crypto.keyring import KeyringStore

    store = KeyringStore(service_name="test-cipherbox")

    class BrokenKeyring:
        @staticmethod
        def set_password(service, username, password):
            raise OSError("keyring locked")

    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", BrokenKeyring)

    with pytest.raises(OSError):
        store.store(tmp_path / "vault", b"\x01" * 32)
