"""Unit tests for app-level key-value config (cipherbox/config/app_config.py)."""

import json

from cipherbox.config.app_config import AppConfig, load_app_config, save_app_config


def test_set_then_get_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file",
        lambda: tmp_path / "app-config.json",
    )

    cfg = AppConfig(tmp_path / "app-config.json")
    cfg.set("default-vault", str(tmp_path / "vault"))
    assert cfg.get("default-vault") == str(tmp_path / "vault")


def test_get_missing_key_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file",
        lambda: tmp_path / "app-config.json",
    )

    cfg = AppConfig(tmp_path / "app-config.json")
    assert cfg.get("default-vault") is None


def test_unset_removes_key(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file",
        lambda: tmp_path / "app-config.json",
    )

    cfg = AppConfig(tmp_path / "app-config.json")
    cfg.set("default-vault", str(tmp_path / "vault"))
    cfg.unset("default-vault")
    assert cfg.get("default-vault") is None


def test_unset_missing_key_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file",
        lambda: tmp_path / "app-config.json",
    )

    cfg = AppConfig(tmp_path / "app-config.json")
    # should not raise
    cfg.unset("default-vault")


def test_missing_config_file_treated_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file",
        lambda: tmp_path / "app-config.json",
    )

    cfg = AppConfig(tmp_path / "app-config.json")
    assert cfg.get("default-vault") is None


def test_corrupt_json_raises_value_error(tmp_path, monkeypatch):
    cfg_file = tmp_path / "app-config.json"
    cfg_file.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file", lambda: cfg_file
    )

    try:
        load_app_config()
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_save_and_load_preserves_data(tmp_path, monkeypatch):
    cfg_file = tmp_path / "app-config.json"
    monkeypatch.setattr(
        "cipherbox.config.app_config._app_config_file", lambda: cfg_file
    )

    save_app_config({"default-vault": str(tmp_path / "vault")})
    cfg = AppConfig(tmp_path / "app-config.json")
    assert cfg.get("default-vault") == str(tmp_path / "vault")

    # verify file is valid json on disk
    raw = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert raw == {"default-vault": str(tmp_path / "vault")}
