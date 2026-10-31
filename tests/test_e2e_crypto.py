"""End-to-end tests for the encrypted vault flow through the CLI."""

import json

from cipherbox.__main__ import main


def _seed_encrypted_vault(tmp_path, monkeypatch, capsys, password="master"):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()  # clear init banner

    from cipherbox.crypto.kdf import default_kdf_params, derive_key
    from cipherbox.crypto.vault import save_vault_crypto
    from cipherbox.domain.entry import Entry
    from cipherbox.storage.repository import VaultRepository

    key = derive_key(password, b"salt1234567890ab", default_kdf_params())
    repo = VaultRepository(vault_dir, key=key)
    entries = [
        Entry(
            id="id-a",
            schema_version=1,
            type="login",
            title="github",
            tags=["dev", "personal"],
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


def test_e2e_encrypted_vault_flow(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys)

    # Right password unlocks; list returns entries, redacted.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2
    assert all(
        all(v == "<redacted>" for v in entry["fields"].values()) for entry in data
    )

    # Search across fields works and redacts fields.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["search", "--path", str(vault_dir), "staging", "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert all(
        all(v == "<redacted>" for v in entry["fields"].values()) for entry in data
    )

    # Wrong password fails.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wrong")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code != 0
    err = capsys.readouterr().err
    assert "secret" not in err.lower()


def test_e2e_password_change_flow(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys)

    # Old password unlocks before change.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2

    # Change password master -> rotate.
    # The 4th input answers the keyring re-store prompt ("n" here).
    inputs = iter(["master", "rotate", "rotate", "n"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(inputs))
    code = main(["password", "change", "--path", str(vault_dir), "--confirm"])
    assert code == 0
    capsys.readouterr()

    # Old password no longer unlocks.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code != 0

    # New password unlocks and entry contents intact.
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "rotate")
    code = main(["list", "--path", str(vault_dir), "--output", "json", "--reveal"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2
    by_id = {e["id"]: e for e in data}
    assert by_id["id-a"]["fields"]["password"] == "secret"
    assert by_id["id-b"]["fields"]["token"] == "sk-xyz"


def test_on_disk_entry_never_contains_plaintext(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys)
    entry_file = vault_dir / "entries" / "id-a.json"
    raw = entry_file.read_text(encoding="utf-8")
    assert "github" not in raw
    assert "alice" not in raw
    assert "secret" not in raw
    assert "cipherbox-vault-enc/1" in raw
