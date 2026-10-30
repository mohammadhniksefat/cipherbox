"""`vault get` command: retrieve a single secret field value or entry metadata."""

from __future__ import annotations

import argparse
import sys

from cipherbox.errors import MissingEntryError, VaultError
from cipherbox.storage.repository import VaultRepository


def get_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """Retrieve an entry's metadata or a single field value.

    Without ``--field``, prints entry metadata with field values redacted.
    With ``--field``, prints only that field's value to stdout. A missing
    entry or field returns a nonzero exit code; secret values never go to
    stderr.
    """
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    field = getattr(args, "field", None)

    try:
        entry = repo.get(args.id)
    except MissingEntryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    if field:
        if field not in entry.fields:
            print(
                f"error: entry {entry.id!r} has no field {field!r}",
                file=sys.stderr,
            )
            return 1
        print(entry.fields[field])
        return 0

    print(f"id:        {entry.id}")
    print(f"type:      {entry.type}")
    print(f"title:     {entry.title}")
    print(f"tags:      {', '.join(entry.tags) or '(none)'}")
    print(f"created:   {entry.created_at}")
    print(f"updated:   {entry.updated_at}")
    if entry.fields:
        print("fields:")
        for key in sorted(entry.fields):
            print(f"  {key}: <redacted>")
    else:
        print("fields: (none)")
    return 0
