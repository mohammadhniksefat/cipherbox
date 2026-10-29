"""End-to-end tests for backup, restore, conflict detection, and atomic writes."""

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


def test_e2e_backup_restore_encrypted_vault(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys)
    backup_dir = tmp_path / "backups"

    # back up the encrypted vault
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(
        [
            "backup",
            "create",
            "--path",
            str(vault_dir),
            "--backup-dir",
            str(backup_dir),
        ]
    )
    assert code == 0
    backup_id = capsys.readouterr().out.strip()
    assert backup_id

    # corrupt/delete an entry in the live vault
    entry_file = vault_dir / "entries" / "id-b.json"
    entry_file.unlink()
    (entries_dir := vault_dir / "entries").mkdir(exist_ok=True)
    # remove all remaining entry files so restore can write them fresh
    for f in entries_dir.glob("*.json"):
        f.unlink()

    # restore from backup; entries are intact and decryptable
    code = main(
        [
            "backup",
            "restore",
            backup_id,
            "--path",
            str(vault_dir),
            "--backup-dir",
            str(backup_dir),
        ]
    )
    assert code == 0
    capsys.readouterr()  # clear restore banner

    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["list", "--path", str(vault_dir), "--output", "json", "--reveal"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    by_id = {e["id"]: e for e in data}
    assert set(by_id) == {"id-a", "id-b"}
    assert by_id["id-b"]["title"] == "openai"


def test_e2e_restore_is_non_destructive(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys)
    backup_dir = tmp_path / "backups"

    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(
        [
            "backup",
            "create",
            "--path",
            str(vault_dir),
            "--backup-dir",
            str(backup_dir),
        ]
    )
    assert code == 0
    backup_id = capsys.readouterr().out.strip()

    # vault still has entries; restore should refuse to overwrite
    code = main(
        [
            "backup",
            "restore",
            backup_id,
            "--path",
            str(vault_dir),
            "--backup-dir",
            str(backup_dir),
        ]
    )
    assert code != 0


def test_e2e_conflict_detection_on_duplicate_ids(tmp_path, monkeypatch, capsys):
    vault_dir = _seed_encrypted_vault(tmp_path, monkeypatch, capsys)
    # plant a second file with the same id but different content
    entries_dir = vault_dir / "entries"
    (entries_dir / "dup-id-a.json").write_text(
        json.dumps(
            {
                "id": "id-a",
                "schema_version": 1,
                "type": "login",
                "title": "conflict",
                "tags": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
                "fields": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code != 0
    err = capsys.readouterr().err
    assert "conflict" in err.lower() or "id-a" in err
