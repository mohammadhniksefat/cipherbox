"""Tests for the `vault keyring store|clear|show` CLI command."""

import json

from cipherbox.__main__ import main


def _seed_encrypted_vault(tmp_path, monkeypatch, password="master-pass"):
    """Initialize an encrypted vault and point app config default-vault at it."""
    import base64

    from cipherbox.crypto.kdf import default_kdf_params, derive_key
    from cipherbox.crypto.vault import save_vault_crypto
    from cipherbox.domain.entry import Entry
    from cipherbox.storage.repository import VaultRepository

    vault_dir = tmp_path / "my-vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0

    key = derive_key(password, b"\x01" * 16, default_kdf_params())
    params = default_kdf_params()
    salt = b"\x01" * 16
    save_vault_crypto(
        vault_dir,
        {
            "encrypted": True,
            "kdf": "argon2id",
            "kdf_params": {
                "time_cost": params.time_cost,
                "memory_cost": params.memory_cost,
                "parallelism": params.parallelism,
                "hash_len": params.hash_len,
            },
            "salt": base64.b64encode(salt).decode("ascii"),
        },
    )
    repo = VaultRepository(vault_dir, key=key)
    entry = Entry(
        id="id-1",
        schema_version=1,
        type="login",
        title="github",
        tags=["dev"],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        fields={"password": "secret"},
    )
    repo.add(entry)
    return vault_dir


def test_keyring_store_then_list_without_prompt(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch)
    capsys.readouterr()  # clear init banner

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

    # Provide master password via getpass mock for `store`.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master-pass")

    code = main(["keyring", "store", "--path", str(vault_dir)])
    assert code == 0
    capsys.readouterr()

    # Now list should use keyring — no prompt needed.
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert any(e["id"] == "id-1" for e in data)


def test_keyring_clear_restores_prompt(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch)
    capsys.readouterr()

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
    fake._data[str(vault_dir.resolve())] = "cached-key"
    monkeypatch.setattr("cipherbox.crypto.keyring._keyring_mod", fake)

    # clear should succeed and remove entry.
    code = main(["keyring", "clear", "--path", str(vault_dir)])
    assert code == 0
    capsys.readouterr()

    # Entry gone → list should fail (mock getpass returns wrong password).
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wrong-password")
    code = main(["list", "--path", str(vault_dir)])
    assert code != 0


def test_keyring_show_reports_presence(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch)
    capsys.readouterr()

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

    # No entry yet.
    code = main(["keyring", "show", "--path", str(vault_dir)])
    assert code == 0
    out = capsys.readouterr().out
    assert "No unlock key stored" in out

    fake._data[str(vault_dir.resolve())] = "cached-key"
    code = main(["keyring", "show", "--path", str(vault_dir)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Unlock key stored" in out
