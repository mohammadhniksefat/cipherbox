"""Tests for the `vault get` command."""

import argparse

from cipherbox.cli.get import get_command
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _make_entry(entry_id: str, title: str) -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type="login",
        title=title,
        tags=["dev"],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        fields={"username": "alice", "password": "s3cret"},
    )


def test_get_field_prints_value_to_stdout(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = get_command(
        argparse.Namespace(id="id-1", field="password", reveal=False),
        repo=repo,
    )
    assert code == 0
    assert capsys.readouterr().out.strip() == "s3cret"


def test_get_no_field_redacts_values(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = get_command(
        argparse.Namespace(id="id-1", field=None, reveal=False),
        repo=repo,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "github" in out
    assert "s3cret" not in out


def test_get_missing_field_errors_nonzero(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = get_command(
        argparse.Namespace(id="id-1", field="token", reveal=False),
        repo=repo,
    )
    assert code != 0
    err = capsys.readouterr().err
    assert "token" in err
    assert "s3cret" not in err


def test_get_missing_entry_errors_nonzero(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)

    code = get_command(
        argparse.Namespace(id="nope", field="password", reveal=False),
        repo=repo,
    )
    assert code != 0
    err = capsys.readouterr().err
    assert "s3cret" not in err
