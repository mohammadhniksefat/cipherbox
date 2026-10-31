"""Tests for default vault resolution (app config -> platform default)."""

import json

from cipherbox.__main__ import main
from cipherbox.config.paths import default_vault_dir, resolve_vault_dir


def _monkeypatch_app_config(tmp_path, monkeypatch, data):
    cfg_file = tmp_path / "app-config.json"
    cfg_file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file", lambda: cfg_file
    )
    return cfg_file


def test_resolve_vault_dir_uses_app_config_default_vault(tmp_path, monkeypatch):
    vault_dir = tmp_path / "my-vault"
    _monkeypatch_app_config(tmp_path, monkeypatch, {"default-vault": str(vault_dir)})
    assert resolve_vault_dir() == vault_dir


def test_resolve_vault_dir_falls_back_to_platform_default(tmp_path, monkeypatch):
    _monkeypatch_app_config(tmp_path, monkeypatch, {})
    assert resolve_vault_dir() == default_vault_dir()


def test_resolve_vault_dir_missing_config_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file",
        lambda: tmp_path / "nonexistent" / "app-config.json",
    )
    assert resolve_vault_dir() == default_vault_dir()


def test_list_without_path_reads_app_config_default_vault(
    tmp_path, monkeypatch, capsys
):
    vault_dir = tmp_path / "my-vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()  # clear init banner

    _monkeypatch_app_config(tmp_path, monkeypatch, {"default-vault": str(vault_dir)})

    assert (
        main(
            [
                "add",
                "--type",
                "login",
                "--title",
                "github",
                "--field",
                "username=alice",
                "--field",
                "password=secret",
            ]
        )
        == 0
    )
    capsys.readouterr()  # clear add banner

    code = main(["list", "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["title"] == "github"


def test_explicit_path_overrides_app_config(tmp_path, monkeypatch, capsys):
    vault_a = tmp_path / "vault-a"
    vault_b = tmp_path / "vault-b"
    assert main(["init", "--path", str(vault_a), "--confirm"]) == 0
    assert main(["init", "--path", str(vault_b), "--confirm"]) == 0

    _monkeypatch_app_config(tmp_path, monkeypatch, {"default-vault": str(vault_a)})

    assert (
        main(
            [
                "add",
                "--path",
                str(vault_a),
                "--type",
                "login",
                "--title",
                "in-a",
                "--field",
                "username=alice",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "add",
                "--path",
                str(vault_b),
                "--type",
                "login",
                "--title",
                "in-b",
                "--field",
                "username=bob",
            ]
        )
        == 0
    )
    capsys.readouterr()  # clear banners

    code = main(["list", "--path", str(vault_b), "--output", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert [entry["title"] for entry in data] == ["in-b"]
