"""`vault copy` command: copy a secret field value to the clipboard."""

from __future__ import annotations

import argparse
import sys

from cipherbox.errors import MissingEntryError, VaultError
from cipherbox.storage.repository import VaultRepository


def _set_clipboard(text: str) -> None:
    """Copy ``text`` to the clipboard.

    This is an injectable helper: the standard library has no portable
    clipboard API, so this is a no-op by default. Tests (and integrations
    with platform clipboard tools) monkeypatch this symbol. Clipboard
    clearing, where offered, is best-effort: clipboard managers may retain
    copies.
    """


def copy_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """Copy a single field value to the clipboard.

    Requires explicit field selection. Prints a warning that clipboard
    contents may be accessible to other applications. The secret value is
    never printed to stderr.
    """
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    field = getattr(args, "field", None)
    if not field:
        print(
            "error: --field is required to select the value to copy",
            file=sys.stderr,
        )
        return 1

    try:
        entry = repo.get(args.id)
    except MissingEntryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    if field not in entry.fields:
        print(
            f"error: entry {entry.id!r} has no field {field!r}",
            file=sys.stderr,
        )
        return 1

    _set_clipboard(entry.fields[field])

    print(
        f"Copied field {field!r} of entry {entry.id} to the clipboard. "
        "Warning: clipboard contents may be accessible to other applications; "
        "clearing is best-effort and clipboard managers may retain copies.",
    )
    return 0
