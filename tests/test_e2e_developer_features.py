"""End-to-end tests for phase 6 developer productivity features."""

from cipherbox.__main__ import main
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _entry(entry_id, type, title, fields, tags=()):
    return Entry(
        id=entry_id,
        schema_version=1,
        type=type,
        title=title,
        tags=list(tags),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        fields=dict(fields),
    )


def _seed(vault_dir, entries):
    repo = VaultRepository(vault_dir)
    repo.init(confirm=True)
    for entry in entries:
        repo.add(entry)
    return repo


def test_e2e_get_returns_field_value(tmp_path, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()
    _seed(
        vault_dir,
        [
            _entry(
                "id-1",
                "login",
                "github",
                {"username": "alice", "password": "s3cret"},
                tags=["dev"],
            )
        ],
    )

    # get --field prints only the value to stdout
    code = main(["get", "--path", str(vault_dir), "id-1", "--field", "password"])
    assert code == 0
    assert capsys.readouterr().out.strip() == "s3cret"

    # get without --field redacts field values
    code = main(["get", "--path", str(vault_dir), "id-1"])
    assert code == 0
    out = capsys.readouterr().out
    assert "github" in out
    assert "s3cret" not in out


def test_e2e_env_list_project_tagged_only(tmp_path, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()
    _seed(
        vault_dir,
        [
            _entry("id-1", "env", "web", {"API_KEY": "secret"}, tags=["my-project"]),
            _entry("id-2", "env", "db", {"DB_URL": "x"}, tags=["other-project"]),
        ],
    )

    code = main(["env", "list", "--path", str(vault_dir), "my-project"])
    assert code == 0
    out = capsys.readouterr().out
    assert "web" in out
    assert "db" not in out
    assert "secret" not in out


def test_e2e_generate_password_length(tmp_path, capsys):
    code = main(["generate", "password", "--length", "20"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert len(out) == 20
    assert out.isalnum()


def test_e2e_check_healthy_vault_exits_zero(tmp_path, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()
    _seed(
        vault_dir,
        [
            _entry("id-1", "login", "github", {"password": "s3cret"}, tags=["dev"]),
        ],
    )

    code = main(["check", "--all", "--path", str(vault_dir)])
    assert code == 0
    out = capsys.readouterr().out
    err = capsys.readouterr().err
    assert "error" not in err.lower()
    assert "s3cret" not in out and "s3cret" not in err


def test_e2e_copy_clipboard_receives_value(tmp_path, capsys, monkeypatch):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()
    _seed(
        vault_dir,
        [
            _entry("id-1", "login", "github", {"token": "abc123"}, tags=["dev"]),
        ],
    )

    captured = {}

    def fake_clipboard(text):
        captured["text"] = text

    import cipherbox.cli.copy as copy_mod

    monkeypatch.setattr(copy_mod, "_set_clipboard", fake_clipboard)

    code = main(["copy", "--path", str(vault_dir), "id-1", "--field", "token"])
    assert code == 0
    assert captured["text"] == "abc123"

    err = capsys.readouterr().err
    assert "abc123" not in err
