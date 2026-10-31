"""Tests for the `vault config show|set|unset` CLI command."""

import json

from cipherbox.__main__ import main


def _set_config(tmp_path, monkeypatch, data):
    """Point the app config at a temp file and seed it with ``data``."""
    cfg_file = tmp_path / "app-config.json"
    cfg_file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file", lambda: cfg_file
    )
    return cfg_file


def test_config_show_existing_key_prints_value(tmp_path, monkeypatch, capsys):
    _set_config(tmp_path, monkeypatch, {"default-vault": str(tmp_path / "vault")})

    code = main(["config", "show", "default-vault"])
    assert code == 0
    out = capsys.readouterr().out
    assert str(tmp_path / "vault") in out


def test_config_show_missing_key_errors(tmp_path, monkeypatch, capsys):
    _set_config(tmp_path, monkeypatch, {})

    code = main(["config", "show", "default-vault"])
    assert code != 0
    err = capsys.readouterr().err
    assert "default-vault" in err


def test_config_set_then_show_roundtrip(tmp_path, monkeypatch, capsys):
    _set_config(tmp_path, monkeypatch, {})

    code = main(["config", "set", "default-vault", str(tmp_path / "vault")])
    assert code == 0
    capsys.readouterr()

    code = main(["config", "show", "default-vault"])
    assert code == 0
    out = capsys.readouterr().out
    assert str(tmp_path / "vault") in out


def test_config_set_requires_value(tmp_path, monkeypatch, capsys):
    _set_config(tmp_path, monkeypatch, {})

    code = main(["config", "set", "default-vault"])
    assert code != 0
    err = capsys.readouterr().err
    assert "error" in err.lower()


def test_config_unset_removes_key(tmp_path, monkeypatch, capsys):
    vault_path = str(tmp_path / "vault")
    _set_config(tmp_path, monkeypatch, {"default-vault": vault_path})

    code = main(["config", "unset", "default-vault"])
    assert code == 0

    code = main(["config", "show", "default-vault"])
    assert code != 0
    err = capsys.readouterr().err
    assert "default-vault" in err


def test_config_unset_missing_key_is_noop(tmp_path, monkeypatch, capsys):
    _set_config(tmp_path, monkeypatch, {})

    code = main(["config", "unset", "default-vault"])
    assert code == 0


def test_config_no_subcommand_errors(tmp_path, monkeypatch, capsys):
    _set_config(tmp_path, monkeypatch, {})

    code = main(["config"])
    assert code != 0


def test_config_list_prints_all_keys(tmp_path, monkeypatch, capsys):
    _set_config(
        tmp_path,
        monkeypatch,
        {"default-vault": str(tmp_path / "vault"), "theme": "dark"},
    )

    code = main(["config", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "default-vault" in out
    assert str(tmp_path / "vault") in out
    assert "theme" in out
    assert "dark" in out


def test_config_list_empty_is_ok(tmp_path, monkeypatch, capsys):
    _set_config(tmp_path, monkeypatch, {})

    code = main(["config", "list"])
    assert code == 0
