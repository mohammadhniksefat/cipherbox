"""Tests for the `vault show` command."""

import argparse

from cipherbox.cli.show import show_command
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
        fields={"username": "alice", "password": "secret"},
    )


def test_show_redacts_fields_by_default(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = show_command(argparse.Namespace(id="id-1", reveal=False), repo=repo)
    assert code == 0
    captured = capsys.readouterr().out
    assert "github" in captured
    assert "secret" not in captured
    assert "alice" not in captured


def test_show_reveals_fields_with_flag(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = show_command(
        argparse.Namespace(id="id-1", reveal=True, long=True), repo=repo
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "secret" in captured


def test_show_missing_entry_returns_nonzero(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    code = show_command(argparse.Namespace(id="nope", reveal=False), repo=repo)
    assert code != 0


def test_show_long_includes_timestamps_and_lengths(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = show_command(
        argparse.Namespace(id="id-1", reveal=False, long=True), repo=repo
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "created:   2026-01-01T00:00:00Z" in captured
    assert "updated:   2026-01-02T00:00:00Z" in captured
    assert "password: 6 chars" in captured
    assert "username: 5 chars" in captured
    # values stay redacted without --reveal
    assert "secret" not in captured
    assert "alice" not in captured


def test_show_long_reveals_values_with_reveal(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = show_command(
        argparse.Namespace(id="id-1", reveal=True, long=True), repo=repo
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "password: secret" in captured
    assert "6 chars" not in captured


def test_show_minimal_omits_timestamps(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = show_command(argparse.Namespace(id="id-1", reveal=False), repo=repo)
    assert code == 0
    captured = capsys.readouterr().out
    assert "github" in captured
    assert "2026" not in captured
    assert "chars" not in captured
