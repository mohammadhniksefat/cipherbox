"""Tests for vault path configuration."""

from cipherbox.config.paths import (
    VaultConfig,
    default_vault_dir,
    load_config,
    save_config,
)


def test_default_vault_dir_returns_a_path():
    path = default_vault_dir()
    assert path is not None
    assert str(path) != ""


def test_vault_config_round_trip(tmp_path):
    config_file = tmp_path / "config.json"
    cfg = VaultConfig(vault_dir=tmp_path / "vault", config_file=config_file)
    save_config(cfg)
    loaded = load_config(config_file)
    assert loaded.vault_dir == cfg.vault_dir
    assert loaded.entries_dir == loaded.vault_dir / "entries"
