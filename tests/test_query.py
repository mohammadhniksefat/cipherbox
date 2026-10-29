"""Tests for the query service: filtering, search, sort, and paginate."""

from cipherbox.domain.entry import Entry
from cipherbox.services.query import (
    EntryQuery,
    FieldQuery,
    filter_entries,
    paginate_entries,
    query_entries,
    sort_entries,
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


def test_type_filter_narrows_to_one_type():
    entries = [
        _make_entry("a", type="login", title="github"),
        _make_entry("b", type="api-key", title="openai"),
    ]
    query = EntryQuery(type="api-key")
    assert [e.id for e in filter_entries(entries, query)] == ["b"]


def test_tag_filters_use_and_semantics():
    entries = [
        _make_entry("a", title="github", tags=("dev", "personal")),
        _make_entry("b", title="gitlab", tags=("dev",)),
    ]
    query = EntryQuery(tags=("dev", "personal"))
    assert [e.id for e in filter_entries(entries, query)] == ["a"]


def test_exact_title_match():
    entries = [
        _make_entry("a", title="GitHub"),
        _make_entry("b", title="gitlab"),
    ]
    query = EntryQuery(title="GitHub")
    assert [e.id for e in filter_entries(entries, query)] == ["a"]


def test_field_query_equals_operates_on_typed_data():
    entries = [
        _make_entry("a", fields={"provider": "openai"}),
        _make_entry("b", fields={"provider": "anthropic"}),
    ]
    query = EntryQuery(field_queries=(FieldQuery("provider", "equals", "openai"),))
    assert [e.id for e in filter_entries(entries, query)] == ["a"]


def test_field_query_contains_operates_on_typed_data():
    entries = [
        _make_entry("a", fields={"hostname": "staging.example.com"}),
        _make_entry("b", fields={"hostname": "prod.example.com"}),
    ]
    query = EntryQuery(field_queries=(FieldQuery("hostname", "contains", "staging"),))
    assert [e.id for e in filter_entries(entries, query)] == ["a"]


def test_text_search_is_case_insensitive_partial_across_title_fields_tags():
    entries = [
        _make_entry("a", title="GitHub", fields={"password": "x"}, tags=("dev",)),
        _make_entry("b", title="GitLab", fields={"password": "y"}, tags=("ops",)),
    ]
    query = EntryQuery(search="hub")
    assert [e.id for e in filter_entries(entries, query)] == ["a"]


def test_search_in_title_only_restricts_to_title():
    entries = [
        _make_entry("a", title="GitHub", fields={"password": "hub-secret"}),
        _make_entry("b", title="GitLab", fields={"password": "x"}),
    ]
    query = EntryQuery(search="hub", search_in=("title",))
    assert [e.id for e in filter_entries(entries, query)] == ["a"]


def test_combined_filters_use_and_semantics():
    entries = [
        _make_entry(
            "a",
            type="login",
            title="github",
            tags=("dev",),
            fields={"provider": "github"},
        ),
        _make_entry(
            "b",
            type="login",
            title="gitlab",
            tags=("dev",),
            fields={"provider": "gitlab"},
        ),
    ]
    query = EntryQuery(type="login", tags=("dev",), search="gitlab")
    assert [e.id for e in filter_entries(entries, query)] == ["b"]


def test_sort_by_title_is_deterministic():
    entries = [
        _make_entry("b", title="zeta"),
        _make_entry("a", title="alpha"),
        _make_entry("c", title="alpha"),
    ]
    ordered = sort_entries(entries, "title")
    ids = [e.id for e in ordered]
    # "alpha" entries tie; tie-break by id for determinism.
    assert ids == ["a", "c", "b"]


def test_sort_by_created_and_updated():
    entries = [
        _make_entry("a", updated="2026-01-02T00:00:00Z"),
        _make_entry("b", updated="2026-01-01T00:00:00Z"),
        _make_entry("c", updated="2026-01-03T00:00:00Z"),
    ]
    ordered = sort_entries(entries, "updated")
    assert [e.id for e in ordered] == ["b", "a", "c"]


def test_paginate_limit_and_offset_returns_stable_slice():
    entries = [_make_entry(str(i), title=f"entry-{i}") for i in range(5)]
    page = paginate_entries(entries, limit=2, offset=1)
    assert [e.id for e in page] == ["1", "2"]


def test_query_entries_filters_sorts_and_paginates():
    entries = [
        _make_entry("a", type="login", title="zeta", tags=("dev",)),
        _make_entry("b", type="api-key", title="alpha", tags=("dev",)),
        _make_entry("c", type="login", title="alpha", tags=("ops",)),
    ]
    query = EntryQuery(type="login", tags=("dev",), sort_by="title", limit=1, offset=0)
    assert [e.id for e in query_entries(entries, query)] == ["a"]


def test_empty_query_returns_all_entries_sorted():
    entries = [
        _make_entry("b", title="zeta"),
        _make_entry("a", title="alpha"),
    ]
    query = EntryQuery()
    assert [e.id for e in query_entries(entries, query)] == ["a", "b"]
