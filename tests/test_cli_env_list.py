"""Tests for the `vault env list` command."""

import argparse

from cipherbox.cli.env import env_list_command
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _make_entry(entry_id: str, title: str, tags: list[str]) -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type="env",
        title=title,
        tags=tags,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        fields={"API_KEY": "secret-value", "HOST": "example.com"},
    )


def test_env_list_shows_only_project_tagged_entries(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "web", ["my-project", "dev"]))
    repo.add(_make_entry("id-2", "db", ["other-project"]))

    code = env_list_command(argparse.Namespace(project="my-project"), repo=repo)
    assert code == 0
    out = capsys.readouterr().out
    assert "web" in out
    assert "db" not in out


def test_env_list_redacts_field_values(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "web", ["my-project"]))

    code = env_list_command(argparse.Namespace(project="my-project"), repo=repo)
    assert code == 0
    out = capsys.readouterr().out
    assert "secret-value" not in out
    assert "<redacted>" in out


def test_env_list_no_matches_prints_no_entries(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "web", ["my-project"]))

    code = env_list_command(argparse.Namespace(project="nope"), repo=repo)
    assert code == 0
    out = capsys.readouterr().out
    assert "(no entries)" in out
