"""`vault search` command: full-text search across entry title, fields, and tags."""

from __future__ import annotations

import argparse
import sys

from cipherbox.services.output import format_json, format_table
from cipherbox.services.query import EntryQuery, query_entries
from cipherbox.storage.repository import VaultRepository


def search_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """Search entries by text across the configured fields and print results."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    query = args.query
    search_in = tuple(
        part.strip()
        for part in getattr(args, "in", "title,fields,tags").split(",")
        if part.strip()
    )

    entry_query = EntryQuery(
        type=getattr(args, "type", None),
        tags=tuple(getattr(args, "tag", []) or []),
        search=query,
        search_in=search_in,
        sort_by=getattr(args, "sort", "title"),
        limit=getattr(args, "limit", None),
        offset=getattr(args, "offset", 0),
    )

    try:
        entries = query_entries(repo.list(), entry_query)
    except Exception as exc:  # noqa: BLE001 - surface repository errors as CLI errors
        print(f"error: {exc}", file=sys.stderr)
        return 1

    reveal = bool(getattr(args, "reveal", False))
    output = getattr(args, "output", "table")

    if output == "json":
        print(format_json(entries, reveal=reveal))
    else:
        print(format_table(entries, reveal=reveal))
    return 0
