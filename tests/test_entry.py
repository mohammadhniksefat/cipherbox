"""Tests for the domain model: Entry, secret types, and validation."""

from cipherbox.domain.entry import (
    SCHEMA_VERSION,
    SECRET_TYPES,
    Entry,
    entry_from_dict,
    entry_to_dict,
    validate_entry,
)
from cipherbox.errors import InvalidEntryError


def test_secret_types_match_spec():
    assert SECRET_TYPES == frozenset(
        {"login", "api-key", "ssh", "secure-note", "env", "recovery"}
    )


def test_schema_version_is_one():
    assert SCHEMA_VERSION == 1


def test_entry_round_trip_preserves_all_fields():
    original = Entry(
        id="00000000-0000-0000-0000-000000000001",
        schema_version=1,
        type="login",
        title="github",
        tags=["dev", "personal"],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        fields={"username": "alice", "password": "secret"},
    )
    assert entry_from_dict(entry_to_dict(original)) == original


def test_invalid_type_is_rejected():
    bad = Entry(
        id="id-1",
        schema_version=1,
        type="not-a-real-type",
        title="x",
        tags=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        fields={},
    )
    try:
        validate_entry(bad)
    except InvalidEntryError:
        pass
    else:
        raise AssertionError("expected InvalidEntryError for invalid type")


def test_missing_required_field_is_rejected():
    data = {
        "id": "id-1",
        "schema_version": 1,
        "type": "login",
        # title missing
        "tags": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {},
    }
    try:
        entry_from_dict(data)
    except InvalidEntryError:
        pass
    else:
        raise AssertionError("expected InvalidEntryError for missing title")


def test_unknown_type_in_dict_is_rejected():
    data = {
        "id": "id-1",
        "schema_version": 1,
        "type": "not-a-real-type",
        "title": "x",
        "tags": [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fields": {},
    }
    try:
        entry_from_dict(data)
    except InvalidEntryError:
        pass
    else:
        raise AssertionError("expected InvalidEntryError for unknown type")
