"""Tests for the `vault delete` command."""

import argparse

from cipherbox.cli.delete import delete_command
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _make_entry(entry_id: str, title: str) -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type="login",
        title=title,
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        fields={},
    )


def test_delete_removes_only_that_entry(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "first"))
    repo.add(_make_entry("id-2", "second"))

    code = delete_command(argparse.Namespace(id="id-1", confirm=True), repo=repo)
    assert code == 0
    assert repo.get("id-2").title == "second"


def test_delete_requires_confirmation_by_default(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "first"))

    code = delete_command(argparse.Namespace(id="id-1", confirm=False), repo=repo)
    assert code != 0
    # entry still present since confirmation was withheld
    assert repo.get("id-1").title == "first"


def test_delete_missing_entry_returns_nonzero(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    code = delete_command(argparse.Namespace(id="nope", confirm=True), repo=repo)
    assert code != 0
