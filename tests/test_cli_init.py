"""Tests for the `vault init` command."""

import argparse

from cipherbox.cli.init import init_command


def _args(**kwargs):
    defaults = {"path": None, "confirm": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_init_returns_zero_on_success(tmp_path):
    vault_dir = tmp_path / "my-vault"
    args = _args(path=str(vault_dir), confirm=True)
    code = init_command(args)
    assert code == 0
    assert vault_dir.exists()
    assert (vault_dir / "entries").exists()
    assert (vault_dir / "config.json").exists()


def test_init_refuses_existing_vault_without_confirm(tmp_path):
    vault_dir = tmp_path / "my-vault"
    vault_dir.mkdir()
    args = _args(path=str(vault_dir), confirm=False)
    code = init_command(args)
    assert code != 0


def test_init_allows_overwrite_with_confirm(tmp_path):
    vault_dir = tmp_path / "my-vault"
    vault_dir.mkdir()
    args = _args(path=str(vault_dir), confirm=True)
    code = init_command(args)
    assert code == 0
    assert (vault_dir / "entries").exists()
