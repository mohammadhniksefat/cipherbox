"""Query service: filter, search, sort, and paginate vault entries.

Operates on typed ``Entry`` objects in memory. Text search is case-insensitive
partial matching; field queries inspect typed ``Entry`` data (``.type``,
``.title``, ``.tags``, ``.fields[name]``), never raw JSON serialization.
Multiple tags use AND semantics (every requested tag must be present).
"""

from __future__ import annotations

from dataclasses import dataclass, field


REDACTED = "<redacted>"


@dataclass(frozen=True)
class FieldQuery:
    """A single field constraint: entry.fields[field] operator value."""

    field: str
    operator: str  # "equals" or "contains"
    value: str


@dataclass(frozen=True)
class EntryQuery:
    """A query over entries: filters, search, sort, and pagination."""

    type: str | None = None
    tags: tuple[str, ...] = ()
    title: str | None = None
    field_queries: tuple[FieldQuery, ...] = ()
    search: str | None = None
    search_in: tuple[str, ...] = ("title", "fields", "tags")
    sort_by: str = "title"
    limit: int | None = None
    offset: int = 0


def _matches_field_query(entry, fq: FieldQuery) -> bool:
    actual = entry.fields.get(fq.field)
    if actual is None:
        return False
    if fq.operator == "equals":
        return actual == fq.value
    if fq.operator == "contains":
        return fq.value in actual
    return False


def _matches_search(entry, query: str, search_in: tuple[str, ...]) -> bool:
    needle = query.lower()
    haystacks = []
    if "title" in search_in:
        haystacks.append(entry.title)
    if "tags" in search_in:
        haystacks.extend(entry.tags)
    if "fields" in search_in:
        haystacks.extend(entry.fields.values())
    return any(needle in h.lower() for h in haystacks)


def filter_entries(entries: list, query: EntryQuery) -> list:
    """Filter entries by type, tags (AND), title, field queries, and text search.

    Filters on different dimensions use AND semantics.
    """
    result = []
    for entry in entries:
        if query.type is not None and entry.type != query.type:
            continue
        if query.tags and not all(tag in entry.tags for tag in query.tags):
            continue
        if query.title is not None and entry.title != query.title:
            continue
        if query.field_queries and not all(
            _matches_field_query(entry, fq) for fq in query.field_queries
        ):
            continue
        if query.search is not None and not _matches_search(
            entry, query.search, query.search_in
        ):
            continue
        result.append(entry)
    return result


def sort_entries(entries: list, sort_by: str = "title") -> list:
    """Sort entries by ``title``, ``created``, or ``updated``.

    Ties break deterministically by ``id``.
    """

    def key(entry):
        if sort_by == "created":
            return (entry.created_at, entry.id)
        if sort_by == "updated":
            return (entry.updated_at, entry.id)
        # default: title
        return (entry.title, entry.id)

    return sorted(entries, key=key)


def paginate_entries(entries: list, limit: int | None = None, offset: int = 0) -> list:
    """Return a stable slice: ``offset`` then ``limit`` items."""
    sliced = entries[offset:]
    if limit is not None:
        sliced = sliced[:limit]
    return sliced


def query_entries(entries: list, query: EntryQuery) -> list:
    """Filter, then sort, then paginate."""
    return paginate_entries(
        sort_entries(filter_entries(entries, query), query.sort_by),
        query.limit,
        query.offset,
    )
