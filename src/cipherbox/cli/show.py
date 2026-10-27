"""`vault show` command implementation."""

from __future__ import annotations

import argparse
import sys

from cipherbox.domain.entry import Entry
from cipherbox.errors import MissingEntryError, VaultError
from cipherbox.storage.repository import VaultRepository


def show_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """Show an entry's metadata, redacting secret fields by default."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    try:
        entry = repo.show(args.id, redact=not getattr(args, "reveal", False))
    except MissingEntryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    print(f"id:        {entry.id}")
    print(f"type:      {entry.type}")
    print(f"title:     {entry.title}")
    print(f"tags:      {', '.join(entry.tags) or '(none)'}")
    print(f"created:   {entry.created_at}")
    print(f"updated:   {entry.updated_at}")
    if entry.fields:
        print("fields:")
        for key in sorted(entry.fields):
            value = entry.fields[key] if getattr(args, "reveal", False) else "<redacted>"
            print(f"  {key}: {value}")
    else:
        print("fields: (none)")
    return 0
