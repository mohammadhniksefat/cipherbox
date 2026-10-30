"""Tests for the `vault copy` command."""

import argparse

from cipherbox.cli.copy import copy_command
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
        fields={"token": "abc123"},
    )


def test_copy_uses_clipboard_helper_with_value(tmp_path, capsys, monkeypatch):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    captured = {}
    monkeypatch.setattr(
        "cipherbox.cli.copy._set_clipboard",
        lambda text: captured.setdefault("text", text),
    )

    code = copy_command(argparse.Namespace(id="id-1", field="token"), repo=repo)
    assert code == 0
    assert captured["text"] == "abc123"

    captured_io = capsys.readouterr()
    # The secret value must not appear on stderr.
    assert "abc123" not in captured_io.err
    # A clipboard accessibility warning should be printed.
    output = captured_io.out + captured_io.err
    assert "clipboard" in output.lower()


def test_copy_missing_entry_errors(tmp_path, capsys, monkeypatch):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)

    calls = []
    monkeypatch.setattr(
        "cipherbox.cli.copy._set_clipboard",
        lambda text: calls.append(text),
    )

    code = copy_command(argparse.Namespace(id="nope", field="token"), repo=repo)
    assert code != 0
    assert calls == []
    err = capsys.readouterr().err
    assert "abc123" not in err


def test_copy_missing_field_errors(tmp_path, capsys, monkeypatch):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    calls = []
    monkeypatch.setattr(
        "cipherbox.cli.copy._set_clipboard",
        lambda text: calls.append(text),
    )

    code = copy_command(argparse.Namespace(id="id-1", field="nonexistent"), repo=repo)
    assert code != 0
    assert calls == []
