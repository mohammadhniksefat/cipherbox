"""Tests for the `vault add` command."""

import argparse

import pytest

from cipherbox.cli.add import add_command
from cipherbox.domain.entry import Entry
from cipherbox.errors import DuplicateIdError
from cipherbox.storage.repository import VaultRepository


def _args(**kwargs):
    defaults = {"type": "login", "title": "github", "fields": [], "confirm": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_add_creates_entry(tmp_path, monkeypatch):
    repo = VaultRepository(tmp_path)
    inputs = iter(["username", "alice", "password", "secret", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    code = add_command(_args(type="login", title="github"), repo=repo)
    assert code == 0

    entries = repo.list()
    assert len(entries) == 1
    assert entries[0].type == "login"
    assert entries[0].title == "github"
    assert entries[0].fields == {"username": "alice", "password": "secret"}
    assert entries[0].id != ""
    assert entries[0].created_at == entries[0].updated_at


def test_add_rejects_invalid_type(tmp_path):
    repo = VaultRepository(tmp_path)
    code = add_command(_args(type="not-a-type", title="x"), repo=repo)
    assert code != 0


def test_add_duplicate_id_rejected(tmp_path):
    repo = VaultRepository(tmp_path)
    existing = Entry(
        id="fixed-id",
        schema_version=1,
        type="login",
        title="first",
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        fields={},
    )
    repo.add(existing)
    try:
        repo.add(existing)
    except DuplicateIdError:
        pass
    else:
        raise AssertionError("expected DuplicateIdError")
