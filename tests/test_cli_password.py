"""Tests for the `vault password change` command."""

import json

from cipherbox.__main__ import main


def _seed_encrypted_vault(tmp_path, monkeypatch, password="oldpass", capsys=None):
    """Init an encrypted vault, add one entry, and write crypto metadata."""
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    if capsys is not None:
        capsys.readouterr()  # clear init's "Initialized vault" line

    from cipherbox.crypto.kdf import default_kdf_params, derive_key
    from cipherbox.crypto.vault import save_vault_crypto
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
            fields={"username": "alice", "password": "secret-token"},
        )
    )
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


def test_password_change_invalidates_old(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys=capsys)

    # Right old password unlocks before change.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "oldpass")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["fields"]["username"] == "<redacted>"

    # Change password oldpass -> newpass (confirmation supplied).
    # The 4th input answers the keyring re-store prompt ("n" here; this test
    # does not exercise keyring behavior).
    inputs = iter(["oldpass", "newpass", "newpass", "n"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(inputs))
    code = main(["password", "change", "--path", str(vault_dir), "--confirm"])
    assert code == 0
    capsys.readouterr()

    # Old password no longer unlocks.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "oldpass")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code != 0
    err = capsys.readouterr().err
    assert "secret" not in err.lower()

    # New password unlocks and entry contents are intact.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "newpass")
    code = main(["list", "--path", str(vault_dir), "--output", "json", "--reveal"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "id-a"
    assert data[0]["fields"]["password"] == "secret-token"
    assert data[0]["fields"]["username"] == "alice"


def test_password_change_wrong_old_password_fails(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys=capsys)

    monkeypatch.setattr("getpass.getpass", lambda prompt="": "not-the-old")
    code = main(["password", "change", "--path", str(vault_dir), "--confirm"])
    assert code != 0


def test_password_change_clears_keyring_and_prompts_restore(
    tmp_path, monkeypatch, capsys
):
    """On password change, stale keyring entry is removed and user is
    prompted to re-store the new derived key."""
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys=capsys)

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

    # Store the old derived key in keyring first.
    from cipherbox.crypto.kdf import default_kdf_params, derive_key

    old_key = derive_key("oldpass", b"\x01" * 16, default_kdf_params())
    fake._data[str(vault_dir.resolve())] = old_key.decode("latin-1")

    # Change password oldpass -> newpass; answer "y" to re-store prompt.
    inputs = iter(["oldpass", "newpass", "newpass", "y"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(inputs))

    code = main(["password", "change", "--path", str(vault_dir), "--confirm"])
    assert code == 0
    capsys.readouterr()

    # Old keyring entry value is gone: erase removed the old derived key,
    # then store replaced it with the new one (user said "y").
    assert fake._data[str(vault_dir.resolve())] != old_key.decode("latin-1")

    # New derived key was stored (user said "y").
    assert str(vault_dir.resolve()) in fake._data

    # New password unlocks.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "newpass")
    code = main(["list", "--path", str(vault_dir), "--output", "json", "--reveal"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "id-a"
