"""`vault edit` command implementation."""

from __future__ import annotations

import argparse
import sys

from cipherbox.errors import MissingEntryError, VaultError
from cipherbox.storage.repository import VaultRepository


def edit_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """Edit an entry, preserving id and created_at while refreshing updated_at."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    field_updates: dict[str, str] = {}
    for item in getattr(args, "field", []) or []:
        if "=" not in item:
            print(
                f"error: invalid field spec {item!r} (use key=value)", file=sys.stderr
            )
            return 2
        key, _, value = item.partition("=")
        field_updates[key.strip()] = value.strip()

    updates: dict = {}
    if field_updates:
        updates["fields"] = field_updates

    try:
        entry = repo.edit(args.id, updates)
    except MissingEntryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    print(f"Edited entry {entry.id} ({entry.title})")
    return 0
