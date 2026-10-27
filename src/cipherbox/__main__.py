"""Application entry point for the ``vault`` CLI."""

from __future__ import annotations

import argparse
import sys

from cipherbox.cli.add import add_command
from cipherbox.cli.delete import delete_command
from cipherbox.cli.edit import edit_command
from cipherbox.cli.init import init_command
from cipherbox.cli.show import show_command
from cipherbox.config.paths import default_vault_dir
from cipherbox.errors import EXIT_OK
from cipherbox.storage.repository import VaultRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vault",
        description="Local-first secrets manager.",
    )
    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser("init", help="Initialize a vault directory.")
    p_init.add_argument("--path", default=None, help="Vault directory path.")
    p_init.add_argument(
        "--confirm", action="store_true", help="Overwrite an existing vault."
    )

    p_add = subparsers.add_parser("add", help="Add a new entry to the vault.")
    p_add.add_argument("--path", default=None, help="Vault directory path.")
    p_add.add_argument("--type", required=True, help="Secret type.")
    p_add.add_argument("--title", required=True, help="Entry title.")
    p_add.add_argument(
        "--field",
        action="append",
        default=[],
        help="Field in key=value form (repeatable).",
    )

    p_show = subparsers.add_parser("show", help="Show an entry's metadata.")
    p_show.add_argument("--path", default=None, help="Vault directory path.")
    p_show.add_argument("id", help="Entry id.")
    p_show.add_argument(
        "--reveal", action="store_true", help="Reveal secret field values."
    )

    p_edit = subparsers.add_parser("edit", help="Edit an existing entry.")
    p_edit.add_argument("--path", default=None, help="Vault directory path.")
    p_edit.add_argument("id", help="Entry id.")
    p_edit.add_argument(
        "--field",
        action="append",
        default=[],
        help="Field in key=value form (repeatable).",
    )

    p_delete = subparsers.add_parser("delete", help="Delete an entry.")
    p_delete.add_argument("--path", default=None, help="Vault directory path.")
    p_delete.add_argument("id", help="Entry id.")
    p_delete.add_argument(
        "--confirm", action="store_true", help="Confirm the deletion."
    )

    return parser


def _repo(args) -> VaultRepository:
    from cipherbox.config.paths import default_vault_dir

    vault_path = getattr(args, "path", None) or default_vault_dir()
    return VaultRepository(vault_path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK

    if args.command == "init":
        return init_command(args)
    if args.command == "add":
        return add_command(args, repo=_repo(args))
    if args.command == "show":
        return show_command(args, repo=_repo(args))
    if args.command == "edit":
        return edit_command(args, repo=_repo(args))
    if args.command == "delete":
        return delete_command(args, repo=_repo(args))

    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
