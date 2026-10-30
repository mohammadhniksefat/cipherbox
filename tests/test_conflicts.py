"""Conflict and external-modification tests (Phase 7).

Entry files are re-read from disk on every `list`/`get` call (no stale
in-memory cache), so externally modified files surface on the next read
rather than being silently cached. Duplicate IDs across files surface as
conflicts rather than being silently resolved.
"""

import argparse
import json

from cipherbox.cli.check import check_command
from cipherbox.domain.entry import Entry
from cipherbox.storage.repository import VaultRepository


def _args(**kwargs) -> argparse.Namespace:
    base = {"all": True, "path": None}
    base.update(kwargs)
    return argparse.Namespace(**base)


def _make_entry(entry_id: str, title: str) -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type="login",
        title=title,
        tags=["dev"],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        fields={"password": "s3cr3t-vault-2"},
    )


def test_external_modification_surfaced_on_read(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    # External process rewrites the entry file on disk (new title).
    entry_file = tmp_path / "entries" / "id-1.json"
    entry_file.write_text(
        json.dumps(
            {
                "id": "id-1",
                "schema_version": 1,
                "type": "login",
                "title": "externally-modified",
                "tags": ["dev"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-03T00:00:00Z",
                "fields": {"password": "s3cr3t-vault-2"},
            }
        ),
        encoding="utf-8",
    )

    # Next read reflects the external modification — no stale cache.
    entry = repo.get("id-1")
    assert entry.title == "externally-modified"
    assert entry.updated_at == "2026-01-03T00:00:00Z"
    err = capsys.readouterr().err
    assert "s3cr3t-vault-2" not in err


def test_external_modification_reflected_in_list(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    entry_file = tmp_path / "entries" / "id-1.json"
    entry_file.write_text(
        json.dumps(
            {
                "id": "id-1",
                "schema_version": 1,
                "type": "login",
                "title": "externally-modified",
                "tags": ["dev"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-03T00:00:00Z",
                "fields": {},
            }
        ),
        encoding="utf-8",
    )

    entries = repo.list()
    assert len(entries) == 1
    assert entries[0].title == "externally-modified"


def test_external_modification_of_encrypted_entry_requires_key(tmp_path, capsys):
    # An externally tampered encrypted envelope fails authentication:
    # check reports it as an error, never decoding partial plaintext.
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))

    entry_file = tmp_path / "entries" / "id-1.json"
    entry_file.write_text(
        json.dumps(
            {
                "format": "cipherbox-vault-enc/1",
                "algorithm": "aes-256-gcm",
                "nonce": "AAAAAAAAAAAAAAAAAAAAAA==",
                "aad": "Y2lwaGVyYm94LWVudHJhZGUtZW52ZWxvcGU=",
                "ciphertext": "tampered-ciphertext",
            }
        ),
        encoding="utf-8",
    )

    code = check_command(_args(path=str(tmp_path)))
    assert code != 0
    err = capsys.readouterr().err
    assert (
        "id-1" in err or "malformed" in err.lower() or "authentication" in err.lower()
    )
    assert "s3cr3t-vault-2" not in err
