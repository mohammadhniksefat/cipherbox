"""`vault import` command: import vault entries from a JSON file.

Validates every entry before modifying the vault (invalid imports never
partially modify the vault). Supports skip/replace/rename collision
policies and --dry-run. Secret values are never printed to stderr or
diagnostics.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cipherbox.errors import VaultError
from cipherbox.import_export import ImportError, ImportPolicy, import_entries
from cipherbox.storage.repository import VaultRepository


def _build_parser(subparsers) -> None:
    p_import = subparsers.add_parser(
        "import", help="Import vault entries from a JSON file."
    )
    p_import.add_argument("--path", default=None, help="Vault directory path.")
    p_import.add_argument("input", help="Export file to import.")
    p_import.add_argument(
        "--policy",
        default="skip",
        choices=["skip", "replace", "rename"],
        help="Collision policy for duplicate entry IDs (skip/replace/rename).",
    )
    p_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Report proposed changes without writing.",
    )


def import_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """Import entries from an export file into the vault."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        vault_path = Path(getattr(args, "path", None) or default_vault_dir())
        repo = VaultRepository(vault_path)

    input_file = Path(args.input)
    policy = ImportPolicy(getattr(args, "policy", "skip"))

    try:
        report = import_entries(
            repo,
            input_file,
            policy=policy,
            dry_run=getattr(args, "dry_run", False),
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    if report.dry_run:
        print(f"Dry run: would import {len(report.imported)} entries")
    else:
        print(
            f"Imported {len(report.imported)} entries "
            f"(skipped={len(report.skipped)}, "
            f"replaced={len(report.replaced)}, "
            f"renamed={len(report.renamed)})"
        )
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0
