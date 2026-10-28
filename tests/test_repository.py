"""Tests for the JSON file storage repository."""

from cipherbox.domain.entry import Entry
from cipherbox.errors import DuplicateIdError, MalformedFileError, MissingEntryError
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

