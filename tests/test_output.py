"""Tests for table and redacted JSON output formatting."""

import json

from cipherbox.domain.entry import Entry
from cipherbox.services.output import (
    REDACTED,
    format_json,
    format_list_minimal,
    format_show_long,
    format_show_minimal,
    format_table,
)


def _make_entry(
    entry_id,
    type="login",
    title="x",
    tags=(),
    fields=None,
    updated="2026-01-01T00:00:00Z",
):
    return Entry(
        id=entry_id,
        schema_version=1,
        type=type,
        title=title,
        tags=list(tags),
        created_at="2026-01-01T00:00:00Z",
        updated_at=updated,
        fields=dict(fields or {}),
    )


def test_table_output_contains_metadata_columns():
    entries = [
        _make_entry(
            "id-1",
            type="login",
            title="github",
            tags=("dev",),
            fields={"username": "alice"},
        ),
    ]
    out = format_table(entries)
    assert "id-1" in out
    assert "login" in out
    assert "github" in out
    assert "dev" in out


def test_table_redacts_field_values_by_default():
    entries = [
        _make_entry("id-1", fields={"password": "secret", "username": "alice"}),
    ]
    out = format_table(entries)
    assert REDACTED in out
    assert "secret" not in out


def test_table_reveals_field_values_with_reveal():
    entries = [
        _make_entry("id-1", fields={"password": "secret"}),
    ]
    out = format_table(entries, reveal=True)
    assert "secret" in out


def test_json_output_is_valid_and_redacts_by_default():
    entries = [
        _make_entry("id-1", fields={"password": "secret"}),
    ]
    out = format_json(entries)
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "id-1"
    assert data[0]["fields"]["password"] == REDACTED


def test_json_reveals_field_values_with_reveal():
    entries = [
        _make_entry("id-1", fields={"password": "secret"}),
    ]
    out = format_json(entries, reveal=True)
    data = json.loads(out)
    assert data[0]["fields"]["password"] == "secret"


def test_list_minimal_shows_id_type_title_only():
    entries = [
        _make_entry(
            "id-1",
            type="login",
            title="github",
            tags=("dev",),
            fields={"password": "secret"},
        ),
        _make_entry("id-2", type="api-key", title="openai"),
    ]
    out = format_list_minimal(entries)
    assert "id-1" in out
    assert "login" in out
    assert "github" in out
    assert "id-2" in out
    assert "api-key" in out
    assert "openai" in out
    # no field values or hints leaked
    assert "secret" not in out
    assert "password" not in out


def test_list_minimal_empty():
    assert format_list_minimal([]) == "(no entries)"


def test_show_minimal_omits_timestamps_and_field_lengths():
    entry = _make_entry(
        "id-1",
        type="login",
        title="github",
        tags=("dev",),
        fields={"password": "secret", "username": "alice"},
    )
    out = format_show_minimal(entry)
    assert "id-1" in out
    assert "login" in out
    assert "github" in out
    assert "dev" in out
    assert "password" in out
    assert "username" in out
    # no timestamps, no lengths, no values
    assert "2026" not in out
    assert "chars" not in out
    assert "secret" not in out


def test_show_long_includes_timestamps_and_field_lengths():
    entry = _make_entry(
        "id-1",
        type="login",
        title="github",
        tags=("dev",),
        fields={"password": "secret"},
        updated="2026-02-01T00:00:00Z",
    )
    out = format_show_long(entry)
    assert "created:   2026-01-01T00:00:00Z" in out
    assert "updated:   2026-02-01T00:00:00Z" in out
    assert "password: 6 chars" in out
    assert "secret" not in out


def test_show_long_reveals_field_values():
    entry = _make_entry(
        "id-1",
        type="login",
        title="github",
        fields={"password": "secret"},
    )
    out = format_show_long(entry, reveal=True)
    assert "password: secret" in out
    assert "6 chars" not in out
