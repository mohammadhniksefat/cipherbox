"""Tests for the JSON file storage repository."""

import json

import pytest

from cipherbox.domain.entry import Entry
from cipherbox.errors import (
    ConflictError,
    DuplicateIdError,
    MalformedFileError,
    MissingEntryError,
)
from cipherbox.storage.repository import VaultRepository


def _make_entry(entry_id: str, title: str = "t", etype: str = "login") -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type=etype,
        title=title,
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        fields={"username": "alice", "password": "secret"},
    )


def test_add_then_get_round_trip(tmp_path):
    repo = VaultRepository(tmp_path)
    entry = _make_entry("id-1", "github")
    repo.add(entry)
    loaded = repo.get("id-1")
    assert loaded == entry


def test_show_redacts_fields_by_default(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "github"))
    shown = repo.show("id-1")
    assert shown.title == "github"
    # field keys are preserved; values are redacted
    assert set(shown.fields.keys()) == {"username", "password"}
    assert shown.fields["username"] == ""
    assert shown.fields["password"] == ""


def test_show_without_redaction_reveals_fields(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "github"))
    shown = repo.show("id-1", redact=False)
    assert shown.fields["password"] == "secret"
    assert shown.fields["username"] == "alice"


def test_add_duplicate_id_raises(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "github"))
    try:
        repo.add(_make_entry("id-1", "duplicate"))
    except DuplicateIdError:
        pass
    else:
        raise AssertionError("expected DuplicateIdError")


def test_get_missing_entry_raises(tmp_path):
    repo = VaultRepository(tmp_path)
    try:
        repo.get("no-such-id")
    except MissingEntryError:
        pass
    else:
        raise AssertionError("expected MissingEntryError")


def test_delete_removes_only_that_entry(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "first"))
    repo.add(_make_entry("id-2", "second"))
    repo.delete("id-1")
    assert repo.get("id-2").title == "second"
    try:
        repo.get("id-1")
    except MissingEntryError:
        pass
    else:
        raise AssertionError("expected MissingEntryError after delete")


def test_malformed_json_raises(tmp_path):
    repo = VaultRepository(tmp_path)
    entries_dir = tmp_path / "entries"
    entries_dir.mkdir(parents=True)
    (entries_dir / "bad-id.json").write_text("{not valid json", encoding="utf-8")
    try:
        repo.get("bad-id")
    except MalformedFileError:
        pass
    else:
        raise AssertionError("expected MalformedFileError")


def test_list_returns_all_entries(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "first"))
    repo.add(_make_entry("id-2", "second"))
    ids = {e.id for e in repo.list()}
    assert ids == {"id-1", "id-2"}


def test_edit_merges_fields_preserving_untouched(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "github"))
    entry = repo.edit("id-1", {"fields": {"password": "newpass"}})
    assert entry.fields["password"] == "newpass"
    assert entry.fields["username"] == "alice"  # untouched field preserved
    assert entry.id == "id-1"
    assert entry.created_at == "2026-01-01T00:00:00Z"


def test_edit_updates_updated_at(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "github"))
    before = repo.get("id-1").updated_at
    repo.edit("id-1", {"title": "renamed"})
    after = repo.get("id-1").updated_at
    assert after != before


# --- encrypted repository tests ---

from cipherbox.crypto.kdf import default_kdf_params, derive_key
from cipherbox.errors import DecryptionError


def _keyed_repo(tmp_path, password="pw"):
    key = derive_key(password, b"salt1234567890ab", default_kdf_params())
    return VaultRepository(tmp_path, key=key)


def _make_entry_encrypted(
    entry_id: str, title: str = "t", etype: str = "login"
) -> Entry:
    return Entry(
        id=entry_id,
        schema_version=1,
        type=etype,
        title=title,
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        fields={"username": "alice", "password": "secret"},
    )


def test_encrypted_add_get_round_trip(tmp_path):
    repo = _keyed_repo(tmp_path)
    entry = _make_entry_encrypted("id-1", "github")
    repo.add(entry)
    assert repo.get("id-1") == entry


def test_encrypted_file_on_disk_is_not_plaintext(tmp_path):
    repo = _keyed_repo(tmp_path)
    repo.add(_make_entry_encrypted("id-1", "github"))
    raw = (tmp_path / "entries" / "id-1.json").read_text(encoding="utf-8")
    assert "github" not in raw
    assert "alice" not in raw
    assert "secret" not in raw


def test_encrypted_wrong_key_decryption_raises(tmp_path):
    key1 = derive_key("pw-a", b"salt1234567890ab", default_kdf_params())
    key2 = derive_key("pw-b", b"salt1234567890ab", default_kdf_params())
    repo1 = VaultRepository(tmp_path, key=key1)
    repo1.add(_make_entry_encrypted("id-1", "x"))
    repo2 = VaultRepository(tmp_path, key=key2)
    with pytest.raises(DecryptionError):
        repo2.get("id-1")


def test_encrypted_no_key_raises(tmp_path):
    key = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    repo = VaultRepository(tmp_path, key=key)
    repo.add(_make_entry_encrypted("id-1", "github"))
    locked = VaultRepository(tmp_path)
    with pytest.raises(DecryptionError):
        locked.get("id-1")
    with pytest.raises(DecryptionError):
        locked.list()


def test_plaintext_repository_still_works(tmp_path):
    repo = VaultRepository(tmp_path)
    entry = _make_entry_encrypted("id-1", "github")
    repo.add(entry)
    assert repo.get("id-1") == entry


def test_list_skips_malformed_but_raises_wrong_key(tmp_path):
    key = derive_key("pw", b"salt1234567890ab", default_kdf_params())
    repo = VaultRepository(tmp_path, key=key)
    repo.add(_make_entry_encrypted("id-1", "first"))
    # wrong-key repo: malformed file should still be skipped, but the
    # encrypted valid file must raise DecryptionError, not be skipped.
    wrong_key = derive_key("other", b"salt1234567890ab", default_kdf_params())
    locked = VaultRepository(tmp_path, key=wrong_key)
    entries_dir = tmp_path / "entries"
    (entries_dir / "bad-id.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(DecryptionError):
        locked.list()


# --- conflict detection tests ---


def test_list_raises_conflict_on_duplicate_ids_across_files(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "first"))
    # plant a second file with the same id but different content
    path = tmp_path / "entries" / "other.json"
    path.write_text(
        json.dumps(
            {
                "id": "id-1",
                "schema_version": 1,
                "type": "login",
                "title": "second",
                "tags": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "fields": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConflictError) as exc_info:
        repo.list()
    message = str(exc_info.value)
    assert "id-1" in message
    assert str(path) in message


def test_detect_conflicts_returns_duplicates_without_raising(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "first"))
    path = tmp_path / "entries" / "other.json"
    path.write_text(
        json.dumps(
            {
                "id": "id-1",
                "schema_version": 1,
                "type": "login",
                "title": "second",
                "tags": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "fields": {},
            }
        ),
        encoding="utf-8",
    )
    conflicts = repo.detect_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0]["id"] == "id-1"
    assert conflicts[0]["file2"] == str(path)


def test_detect_conflicts_empty_when_no_duplicates(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "first"))
    repo.add(_make_entry("id-2", "second"))
    assert repo.detect_conflicts() == []


def test_atomic_write_leaves_no_temp_and_round_trips(tmp_path):
    repo = VaultRepository(tmp_path)
    entry = _make_entry("id-1", "github")
    repo.add(entry)
    entry_file = tmp_path / "entries" / "id-1.json"
    assert entry_file.exists()
    assert not list(tmp_path.glob("entries/*.tmp"))
    assert repo.get("id-1") == entry


def test_reload_on_next_access_sees_external_modification(tmp_path):
    repo = VaultRepository(tmp_path)
    repo.add(_make_entry("id-1", "first"))
    # externally modify the file on disk
    entry_file = tmp_path / "entries" / "id-1.json"
    entry_file.write_text(
        json.dumps(
            {
                "id": "id-1",
                "schema_version": 1,
                "type": "login",
                "title": "second",
                "tags": [],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
                "fields": {},
            }
        ),
        encoding="utf-8",
    )
    assert repo.get("id-1").title == "second"
