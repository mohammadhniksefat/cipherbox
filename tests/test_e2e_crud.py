"""End-to-end tests exercising the complete CRUD flow through the CLI."""

from cipherbox.__main__ import main


def test_main_no_command_prints_help(capsys):
    code = main([])
    assert code == 0
    captured = capsys.readouterr()
    assert "init" in captured.out
    assert "add" in captured.out


def test_e2e_crud_flow(tmp_path):
    vault_dir = tmp_path / "vault"

    # init
    code = main(["init", "--path", str(vault_dir), "--confirm"])
    assert code == 0
    assert (vault_dir / "entries").exists()

    # add (fields supplied on command line, no interactive prompt)
    code = main([
        "add", "--path", str(vault_dir),
        "--type", "login", "--title", "github",
        "--field", "username=alice", "--field", "password=secret",
    ])
    assert code == 0

    from cipherbox.storage.repository import VaultRepository

    repo = VaultRepository(vault_dir)
    entries = repo.list()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.title == "github"
    assert entry.fields == {"username": "alice", "password": "secret"}
    entry_id = entry.id

    # show (redacted)
    code = main(["show", "--path", str(vault_dir), entry_id])
    assert code == 0

    # edit
    code = main([
        "edit", "--path", str(vault_dir), entry_id,
        "--field", "password=newpass",
    ])
    assert code == 0
    assert repo.get(entry_id).fields["password"] == "newpass"
    assert repo.get(entry_id).id == entry_id  # id preserved
    assert repo.get(entry_id).created_at == entry.created_at  # created_at preserved

    # show redacted still hides values
    code = main(["show", "--path", str(vault_dir), entry_id])
    assert code == 0

    # delete
    code = main(["delete", "--path", str(vault_dir), entry_id, "--confirm"])
    assert code == 0
    try:
        repo.get(entry_id)
    except Exception:
        pass
    else:
        raise AssertionError("entry should be gone after delete")
    assert len(repo.list()) == 0
