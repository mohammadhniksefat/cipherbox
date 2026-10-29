"""End-to-end tests for vault list and search through the CLI."""

import json

from cipherbox.__main__ import main
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _seed(repo_path, entries):
    repo = VaultRepository(repo_path)
    for entry in entries:
        repo.add(entry)
    return repo


def _entry(entry_id, type, title, fields, tags=(), updated="2026-01-01T00:00:00Z"):
    return Entry(
        id=entry_id,
        schema_version=1,
        type=type,
        title=title,
        tags=list(tags),
        created_at="2026-01-01T00:00:00Z",
        updated_at=updated,
        fields=dict(fields),
    )


def test_e2e_list_filters_and_redacts_json(tmp_path, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()

    _seed(
        vault_dir,
        [
            _entry(
                "id-a",
                "login",
                "github",
                {"username": "alice", "password": "secret"},
                tags=["dev", "personal"],
            ),
            _entry(
                "id-b",
                "api-key",
                "openai",
                {"provider": "openai", "token": "sk-xyz"},
                tags=["dev"],
            ),
            _entry(
                "id-c",
                "login",
                "gitlab",
                {"hostname": "staging.gitlab.example.com"},
                tags=["ops"],
            ),
        ],
    )

    # list --type login --tag dev --tag personal --output json: AND semantics
    code = main(
        [
            "list",
            "--path",
            str(vault_dir),
            "--type",
            "login",
            "--tag",
            "dev",
            "--tag",
            "personal",
            "--output",
            "json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    ids = [entry["id"] for entry in data]
    assert "id-a" in ids, f"expected github entry in results, got {ids}"
    # field values redacted by default
    assert all(
        all(v == "<redacted>" for v in entry["fields"].values()) for entry in data
    )


def test_e2e_search_matches_field_value(tmp_path, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()
    _seed(
        vault_dir,
        [
            _entry(
                "id-b",
                "api-key",
                "openai",
                {"provider": "openai", "token": "sk-staging-token"},
                tags=["dev"],
            )
        ],
    )

    code = main(
        [
            "search",
            "--path",
            str(vault_dir),
            "staging",
            "--in",
            "fields",
            "--output",
            "json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["fields"]["token"] == "<redacted>"


def test_e2e_list_sorted_by_updated_is_deterministic(tmp_path, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()
    _seed(
        vault_dir,
        [
            _entry(
                "id-1",
                "login",
                "zeta",
                {"a": "1"},
                tags=["dev"],
                updated="2026-01-02T00:00:00Z",
            ),
            _entry(
                "id-2",
                "login",
                "alpha",
                {"a": "2"},
                tags=["dev"],
                updated="2026-01-01T00:00:00Z",
            ),
        ],
    )

    code = main(
        [
            "list",
            "--path",
            str(vault_dir),
            "--type",
            "login",
            "--tag",
            "dev",
            "--sort",
            "updated",
            "--output",
            "json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2
    assert [entry["id"] for entry in data] == ["id-2", "id-1"]
