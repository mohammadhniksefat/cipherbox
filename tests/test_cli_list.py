"""Tests for the `vault list` command."""

import argparse
import json

import pytest

from cipherbox.cli.list import list_command
from cipherbox.domain.entry import Entry
from cipherbox.errors import DuplicateIdError
from cipherbox.storage.repository import VaultRepository


def _args(**kwargs):
    defaults = {
        "type": None,
        "tag": [],
        "title": None,
        "field": [],
        "equals": [],
        "contains": [],
        "sort": "title",
        "limit": None,
        "offset": 0,
        "output": "table",
        "reveal": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _seed(repo):
    entries = [
        Entry(
            id="id-a",
            schema_version=1,
            type="login",
            title="github",
            tags=["dev", "personal"],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            fields={"username": "alice", "password": "secret"},
        ),
        Entry(
            id="id-b",
            schema_version=1,
            type="api-key",
            title="openai",
            tags=["dev"],
            created_at="2026-01-02T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
            fields={"provider": "openai", "token": "sk-xyz"},
        ),
        Entry(
            id="id-c",
            schema_version=1,
            type="login",
            title="gitlab",
            tags=["ops"],
            created_at="2026-01-03T00:00:00Z",
            updated_at="2026-01-03T00:00:00Z",
            fields={"hostname": "staging.gitlab.example.com"},
        ),
    ]
    for entry in entries:
        repo.add(entry)
    return entries


def test_list_prints_all_entries_in_table(tmp_path):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = list_command(_args(output="table"), repo=repo)
    assert code == 0


def test_list_filters_by_type(tmp_path):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = list_command(_args(type="api-key", output="json"), repo=repo)
    assert code == 0


def test_list_tags_use_and_semantics(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = list_command(_args(tag=["dev", "personal"], output="json"), repo=repo)
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert [entry["id"] for entry in data] == ["id-a"]


def test_list_json_output_is_valid_and_redacted(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = list_command(_args(output="json"), repo=repo)
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 3
    # field values redacted by default
    assert all(
        all(v == "<redacted>" for v in entry["fields"].values()) for entry in data
    )


def test_list_json_reveals_with_reveal(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = list_command(_args(output="json", reveal=True), repo=repo)
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    github = next(e for e in data if e["id"] == "id-a")
    assert github["fields"]["password"] == "secret"


def test_list_field_query_equals(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = list_command(
        _args(field=["provider"], equals=["openai"], output="json"), repo=repo
    )
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert [entry["id"] for entry in data] == ["id-b"]
