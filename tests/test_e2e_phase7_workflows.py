"""End-to-end integration tests for complete user workflows (Phase 7).

These drive the real CLI entry point (`cipherbox.__main__:main`) end to end
through subprocess-like in-process calls, covering the acceptance-criteria
flow: install → init → create encrypted entries → search/retrieve → sync
(backup/restore) → export → restore, using only the documented commands.
"""

import json

from cipherbox.__main__ import main


def _seed_plaintext(vault_dir):
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0


def _add_login(vault_dir, entry_id_override=None):
    args = [
        "add",
        "--path",
        str(vault_dir),
        "--type",
        "login",
        "--title",
        "github",
        "--field",
        "username=alice",
        "--field",
        "password=s3cret",
    ]
    assert main(args) == 0


def _list_ids(vault_dir, capsys, password="master"):
    code = main(["list", "--path", str(vault_dir), "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    return [entry["id"] for entry in data]


def _seed_encrypted(vault_dir, monkeypatch, capsys, password="master"):
    """Seed an encrypted vault, bypassing the CLI password prompt for setup."""
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
            fields={"username": "alice", "password": "s3cr3t-vault-1"},
        ),
        Entry(
            id="id-b",
            schema_version=1,
            type="api-key",
            title="openai",
            tags=["dev"],
            created_at="2026-01-02T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
            fields={"provider": "openai", "token": "sk-live-xyz123"},
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


def test_e2e_plaintext_full_workflow(tmp_path, capsys, monkeypatch):
    vault_dir = tmp_path / "vault"
    backup_dir = tmp_path / "backups"

    _seed_plaintext(vault_dir)
    capsys.readouterr()
    _add_login(vault_dir)
    capsys.readouterr()

    entry_id = _list_ids(vault_dir, capsys)[0]

    # get --field prints only the value to stdout, nothing on stderr.
    code = main(["get", "--path", str(vault_dir), entry_id, "--field", "password"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    err = capsys.readouterr().err
    assert out == "s3cret"
    assert "s3cret" not in err
    # search finds the entry.
    code = main(["search", "--path", str(vault_dir), "github", "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert any(entry["id"] == entry_id for entry in data)

    # export writes a portable JSON document.
    export_file = tmp_path / "export.json"
    code = main(["export", "--path", str(vault_dir), "--output", str(export_file)])
    assert code == 0
    err = capsys.readouterr().err
    assert "s3cret" not in err

    # backup create + restore.
    code = main(
        ["backup", "create", "--path", str(vault_dir), "--backup-dir", str(backup_dir)]
    )
    assert code == 0
    capsys.readouterr()

    # Remove the entry, then restore it.
    main(["delete", "--path", str(vault_dir), entry_id, "--confirm"])
    capsys.readouterr()
    assert len(_list_ids(vault_dir, capsys)) == 0

    backup_id = next(p.name for p in backup_dir.iterdir() if p.is_dir())
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
    capsys.readouterr()
    ids_after = _list_ids(vault_dir, capsys)
    assert entry_id in ids_after

    # check --all exits 0 on the healthy restored vault.
    code = main(["check", "--all", "--path", str(vault_dir)])
    assert code == 0
    err = capsys.readouterr().err
    assert "error" not in err.lower()


def test_e2e_encrypted_full_workflow(tmp_path, monkeypatch, capsys):
    vault_dir = tmp_path / "vault"
    backup_dir = tmp_path / "backups"

    _seed_encrypted(vault_dir, monkeypatch, capsys)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "master")

    entry_id = _list_ids(vault_dir, capsys)[0]

    # get --field returns the decrypted value on an encrypted vault.
    code = main(["get", "--path", str(vault_dir), entry_id, "--field", "password"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    err = capsys.readouterr().err
    assert out == "s3cr3t-vault-1"
    assert "s3cr3t-vault-1" not in err

    # export on an encrypted vault.
    export_file = tmp_path / "export-enc.json"
    code = main(["export", "--path", str(vault_dir), "--output", str(export_file)])
    assert code == 0
    err = capsys.readouterr().err
    assert "s3cr3t-vault-1" not in err
    assert "sk-live-xyz123" not in err

    # backup + restore on an encrypted vault.
    code = main(
        ["backup", "create", "--path", str(vault_dir), "--backup-dir", str(backup_dir)]
    )
    assert code == 0
    capsys.readouterr()

    # Remove the entries, then restore them.
    main(["delete", "--path", str(vault_dir), "id-a", "--confirm"])
    main(["delete", "--path", str(vault_dir), "id-b", "--confirm"])
    capsys.readouterr()
    assert len(_list_ids(vault_dir, capsys)) == 0

    backup_id = next(p.name for p in backup_dir.iterdir() if p.is_dir())
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
    capsys.readouterr()
    ids_after = _list_ids(vault_dir, capsys)
    assert "id-a" in ids_after
    assert "id-b" in ids_after

    # check --all on the encrypted vault never exposes decrypted contents.
    code = main(["check", "--all", "--path", str(vault_dir)])
    assert code == 0
    out = capsys.readouterr().out
    err = capsys.readouterr().err
    assert "s3cr3t-vault-1" not in out and "s3cr3t-vault-1" not in err
    assert "sk-live-xyz123" not in out and "sk-live-xyz123" not in err
