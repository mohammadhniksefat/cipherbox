"""Application entry point for the ``vault`` CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cipherbox.cli.add import add_command
from cipherbox.cli.backup import _build_parser as _build_backup_parser
from cipherbox.cli.backup import (
    backup_create_command,
    backup_list_command,
    backup_restore_command,
)
from cipherbox.cli.delete import delete_command
from cipherbox.cli.edit import edit_command
from cipherbox.cli.init import init_command
from cipherbox.cli.list import list_command
from cipherbox.cli.password import password_change_command
from cipherbox.cli.search import search_command
from cipherbox.cli.show import show_command
from cipherbox.config.paths import default_vault_dir
from cipherbox.errors import EXIT_OK, VaultError
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

    p_list = subparsers.add_parser("list", help="List vault entries with filters.")
    p_list.add_argument("--path", default=None, help="Vault directory path.")
    p_list.add_argument("--type", default=None, help="Filter by entry type.")
    p_list.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Filter by tag (repeatable; uses AND semantics).",
    )
    p_list.add_argument("--title", default=None, help="Filter by exact title match.")
    p_list.add_argument(
        "--field",
        action="append",
        default=[],
        help="Field to constrain (repeatable; pair with --equals or --contains).",
    )
    p_list.add_argument(
        "--equals",
        action="append",
        default=[],
        help="Exact value for the corresponding --field (repeatable).",
    )
    p_list.add_argument(
        "--contains",
        action="append",
        default=[],
        help="Substring value for the corresponding --field (repeatable).",
    )
    p_list.add_argument(
        "--sort",
        default="title",
        choices=["title", "created", "updated"],
        help="Sort by title, created, or updated.",
    )
    p_list.add_argument(
        "--limit", type=int, default=None, help="Maximum number of entries to return."
    )
    p_list.add_argument(
        "--offset", type=int, default=0, help="Number of entries to skip."
    )
    p_list.add_argument(
        "--output",
        default="table",
        choices=["table", "json"],
        help="Output format.",
    )
    p_list.add_argument(
        "--reveal", action="store_true", help="Reveal secret field values."
    )

    p_search = subparsers.add_parser("search", help="Search vault entries by text.")
    p_search.add_argument("--path", default=None, help="Vault directory path.")
    p_search.add_argument("query", help="Text query (case-insensitive partial match).")
    p_search.add_argument(
        "--in",
        default="title,fields,tags",
        help="Comma-separated fields to search: title, fields, tags.",
    )
    p_search.add_argument("--type", default=None, help="Filter by entry type.")
    p_search.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Filter by tag (repeatable; uses AND semantics).",
    )
    p_search.add_argument(
        "--sort",
        default="title",
        choices=["title", "created", "updated"],
        help="Sort by title, created, or updated.",
    )
    p_search.add_argument(
        "--limit", type=int, default=None, help="Maximum number of entries to return."
    )
    p_search.add_argument(
        "--offset", type=int, default=0, help="Number of entries to skip."
    )
    p_search.add_argument(
        "--output",
        default="table",
        choices=["table", "json"],
        help="Output format.",
    )
    p_search.add_argument(
        "--reveal", action="store_true", help="Reveal secret field values."
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

    p_password = subparsers.add_parser("password", help="Password management.")
    p_password_sub = p_password.add_subparsers(dest="password_command")
    p_password_change = p_password_sub.add_parser(
        "change", help="Change the vault master password."
    )
    p_password_change.add_argument("--path", default=None, help="Vault directory path.")
    p_password_change.add_argument(
        "--confirm", action="store_true", help=argparse.SUPPRESS
    )

    _build_backup_parser(subparsers)

    return parser


def _repo(args) -> VaultRepository:
    """Open the vault, unlocking it with a hidden password prompt when encrypted.

    ``init`` is excluded from prompting (it creates the vault). For an
    encrypted vault the master password is read through ``getpass`` (never
    a CLI argument), the key is derived with Argon2id, and an unlocked
    repository is returned. A wrong password raises ``DecryptionError``.
    """
    import base64

    from cipherbox.crypto.kdf import kdf_params_from_dict
    from cipherbox.crypto.vault import (
        VaultKeyManager,
        load_vault_crypto,
        prompt_password,
    )

    vault_path = Path(getattr(args, "path", None) or default_vault_dir())

    # ``init`` creates the vault (no prompt). ``password change`` manages
    # its own unlock flow (old password, then new password + confirmation),
    # so it must not be auto-unlocked here.
    if args.command in ("init", "password"):
        return VaultRepository(vault_path)

    try:
        meta = load_vault_crypto(vault_path)
    except FileNotFoundError:
        # Vault not initialized yet; plaintext repository.
        return VaultRepository(vault_path)

    if not meta.get("encrypted"):
        return VaultRepository(vault_path)

    password = prompt_password()
    salt = base64.b64decode(meta["salt"])
    params = kdf_params_from_dict(meta["kdf_params"])
    mgr = VaultKeyManager()
    try:
        key = mgr.unlock(password, salt, params)
    except Exception as exc:
        raise VaultError(f"failed to unlock vault: {exc}") from exc
    return VaultRepository(vault_path, key=key)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK

    try:
        if args.command == "init":
            return init_command(args)
        if args.command == "add":
            return add_command(args, repo=_repo(args))
        if args.command == "list":
            return list_command(args, repo=_repo(args))
        if args.command == "search":
            return search_command(args, repo=_repo(args))
        if args.command == "show":
            return show_command(args, repo=_repo(args))
        if args.command == "edit":
            return edit_command(args, repo=_repo(args))
        if args.command == "delete":
            return delete_command(args, repo=_repo(args))
        if args.command == "password":
            return password_change_command(args, repo=_repo(args))
        if args.command == "backup":
            if args.backup_command == "create":
                return backup_create_command(args)
            if args.backup_command == "list":
                return backup_list_command(args)
            if args.backup_command == "restore":
                return backup_restore_command(args)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
