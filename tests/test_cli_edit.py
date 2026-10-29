"""Tests for the `vault edit` command."""

import argparse

from cipherbox.cli.edit import edit_command
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


def test_edit_updates_fields_and_refreshes_updated_at(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    code = edit_command(
        argparse.Namespace(id="id-1", field=["password=newpass"]), repo=repo
    )
    assert code == 0

    entry = repo.get("id-1")
    assert entry.fields["password"] == "newpass"
    assert entry.fields["username"] == "alice"  # untouched field preserved
    assert entry.id == "id-1"  # id unchanged
    assert entry.created_at == "2026-01-01T00:00:00Z"  # created_at unchanged
    assert entry.updated_at != "2026-01-02T00:00:00Z"  # updated_at refreshed


def test_edit_missing_entry_returns_nonzero(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    code = edit_command(argparse.Namespace(id="nope", field=["x=y"]), repo=repo)
    assert code != 0
