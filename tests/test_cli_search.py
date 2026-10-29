"""Tests for the `vault search` command."""

import argparse
import json

from cipherbox.cli.search import search_command
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _args(**kwargs):
    defaults = {
        "query": None,
        "in": "title,fields,tags",
        "type": None,
        "tag": [],
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
            tags=["dev"],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            fields={"username": "alice", "password": "secret"},
        ),
        Entry(
            id="id-b",
            schema_version=1,
            type="api-key",
            title="openai",
            tags=["dev", "staging"],
            created_at="2026-01-02T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
            fields={"provider": "openai", "token": "sk-staging-token"},
        ),
        Entry(
            id="id-c",
            schema_version=1,
            type="login",
            title="gitlab",
            tags=["ops"],
            created_at="2026-01-03T00:00:00Z",
            updated_at="2026-01-03T00:00:00Z",
            fields={"hostname": "gitlab.example.com"},
        ),
    ]
    for entry in entries:
        repo.add(entry)
    return entries


def test_search_matches_case_insensitive_partial_across_fields(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = search_command(_args(query="hub", output="json"), repo=repo)
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert [entry["id"] for entry in data] == ["id-a"]


def test_search_in_title_only_restricts_to_title(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    # "staging" appears in id-b's token field but not its title; id-b title is "openai".
    code = search_command(
        _args(query="staging", **{"in": "title"}, output="json"), repo=repo
    )
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == []


def test_search_in_fields_matches_field_value(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = search_command(
        _args(query="staging", **{"in": "fields"}, output="json"), repo=repo
    )
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert [entry["id"] for entry in data] == ["id-b"]


def test_search_json_redacts_fields_by_default(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    _seed(repo)

    code = search_command(_args(query="openai", output="json"), repo=repo)
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 1
    assert data[0]["fields"]["token"] == "<redacted>"
