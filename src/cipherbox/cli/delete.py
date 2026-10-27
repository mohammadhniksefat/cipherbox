"""`vault delete` command implementation."""

from __future__ import annotations

import argparse
import sys

from cipherbox.errors import MissingEntryError, VaultError
from cipherbox.storage.repository import VaultRepository


def delete_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """Delete an entry. Requires confirmation unless explicitly overridden."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    if not getattr(args, "confirm", False):
        print("error: deletion requires confirmation (pass --confirm)", file=sys.stderr)
        return 5

    try:
        repo.delete(args.id)
    except MissingEntryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    print(f"Deleted entry {args.id}")
    return 0
