"""`vault show` command implementation."""

from __future__ import annotations

import argparse
import sys

from cipherbox.errors import MissingEntryError, VaultError
from cipherbox.services.output import format_show_full
from cipherbox.storage.repository import VaultRepository


def show_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """Show an entry's complete metadata, redacting secret fields by default.

    Use --reveal to expose secret field values.
    """
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    try:
        entry = repo.get(args.id)
    except MissingEntryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    reveal = bool(getattr(args, "reveal", False))
    print(format_show_full(entry, reveal=reveal))
    return 0
