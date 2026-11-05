"""`vault list` command: filtered, sorted, paginated entry listing."""

from __future__ import annotations

import argparse
import sys

from cipherbox.services.output import format_json, format_list_minimal
from cipherbox.services.query import EntryQuery, FieldQuery, query_entries
from cipherbox.storage.repository import VaultRepository


def _build_field_queries(args: argparse.Namespace) -> tuple[FieldQuery, ...]:
    fields = list(getattr(args, "field", []) or [])
    equals = list(getattr(args, "equals", []) or [])
    contains = list(getattr(args, "contains", []) or [])
    queries: list[FieldQuery] = []
    n = max(len(fields), len(equals), len(contains))
    for index in range(n):
        if index >= len(fields):
            continue
        field = fields[index]
        value: str | None = None
        operator = "equals"
        if index < len(equals) and equals[index] is not None:
            value = equals[index]
            operator = "equals"
        elif index < len(contains) and contains[index] is not None:
            value = contains[index]
            operator = "contains"
        else:
            continue
        queries.append(FieldQuery(field=field, operator=operator, value=value))
    return tuple(queries)


def list_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """List entries with optional filters, sorting, pagination, and output format."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    query = EntryQuery(
        type=getattr(args, "type", None),
        tags=tuple(getattr(args, "tag", []) or []),
        title=getattr(args, "title", None),
        field_queries=_build_field_queries(args),
        sort_by=getattr(args, "sort", "title"),
        limit=getattr(args, "limit", None),
        offset=getattr(args, "offset", 0),
    )

    try:
        entries = query_entries(repo.list(), query)
    except Exception as exc:  # noqa: BLE001 - surface repository errors as CLI errors
        print(f"error: {exc}", file=sys.stderr)
        return 1

    reveal = bool(getattr(args, "reveal", False))
    output = getattr(args, "output", "table")

    if output == "json":
        print(format_json(entries, reveal=reveal))
    else:
        print(format_list_minimal(entries))
    return 0
