"""`vault export` command: serialize the vault to a documented JSON schema.

Plaintext export: prints a warning to stderr and refuses to overwrite an
existing output file unless --confirm is passed. Secret values are never
printed to stderr or diagnostics.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cipherbox.errors import VaultError
from cipherbox.import_export import EXPORT_FORMAT, ExportError, export_entries
from cipherbox.storage.repository import VaultRepository


def _build_parser(subparsers) -> None:
    p_export = subparsers.add_parser(
        "export", help="Export vault entries to a JSON file."
    )
    p_export.add_argument("--path", default=None, help="Vault directory path.")
    p_export.add_argument(
        "--format",
        default=EXPORT_FORMAT,
        help="Export format (cipherbox-export/1).",
    )
    p_export.add_argument(
        "--output",
        required=True,
        help="Output file path.",
    )
    p_export.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm overwrite of an existing output file.",
    )


def export_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """Export vault entries to a JSON document.

    Warns that the output is plaintext, refuses to overwrite an existing
    file unless --confirm, and writes a ``cipherbox-export/1`` document.
    """
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        vault_path = Path(getattr(args, "path", None) or default_vault_dir())
        repo = VaultRepository(vault_path)

    output = Path(args.output)

    # Plaintext warning: export writes secret-bearing data in decoded form.
    print(
        "warning: export writes secret values in decoded plaintext; "
        "protect the output file like a secret",
        file=sys.stderr,
    )

    try:
        export_entries(
            repo,
            output,
            format=getattr(args, "format", EXPORT_FORMAT),
            overwrite=getattr(args, "confirm", False),
        )
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    print(f"Exported {len(repo.list())} entries to {output}")
    return 0
