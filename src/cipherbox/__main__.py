"""Application entry point for the ``vault`` CLI."""

from __future__ import annotations

import argparse
import sys

from cipherbox.cli.add import add_command
from cipherbox.cli.backup import _build_parser as _build_backup_parser
from cipherbox.cli.backup import (
    backup_create_command,
    backup_list_command,
    backup_restore_command,
)
from cipherbox.cli.check import check_command, doctor_command
from cipherbox.cli.completion import completion_command
from cipherbox.cli.config import config_command
from cipherbox.cli.copy import copy_command
from cipherbox.cli.delete import delete_command
from cipherbox.cli.edit import edit_command
from cipherbox.cli.env import env_export_command, env_list_command
from cipherbox.cli.export import export_command
from cipherbox.cli.generate import generate_password_command
from cipherbox.cli.get import get_command
from cipherbox.cli.import_ import import_command
from cipherbox.cli.init import init_command
from cipherbox.cli.keyring import keyring_command
from cipherbox.cli.list import list_command
from cipherbox.cli.password import password_change_command
from cipherbox.cli.search import search_command
from cipherbox.cli.show import show_command
from cipherbox.cli.unlock import unlock_repo
from cipherbox.config.paths import resolve_vault_dir
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
    p_list.add_argument(
        "--long",
        action="store_true",
        help="Show richer metadata: tags, timestamps, and per-field char length.",
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

    p_get = subparsers.add_parser(
        "get", help="Retrieve an entry's field value or metadata."
    )
    p_get.add_argument("--path", default=None, help="Vault directory path.")
    p_get.add_argument("id", help="Entry id.")
    p_get.add_argument(
        "--field", default=None, help="Print only this field's value to stdout."
    )
    p_get.add_argument(
        "--reveal", action="store_true", help="Reveal secret field values."
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

    p_generate = subparsers.add_parser("generate", help="Generate secrets.")
    p_generate_sub = p_generate.add_subparsers(dest="generate_command")
    p_generate_password = p_generate_sub.add_parser(
        "password", help="Generate a secure password."
    )
    p_generate_password.add_argument(
        "--path", default=None, help="Vault directory path."
    )
    p_generate_password.add_argument(
        "--length",
        type=int,
        default=32,
        help="Password length (default 32).",
    )
    p_generate_password.add_argument(
        "--charset",
        default="lower,digits",
        help="Comma-separated charset pool: lower,upper,digits,punctuation.",
    )

    p_check = subparsers.add_parser(
        "check", help="Validate the vault schema and entries."
    )
    p_check.add_argument("--path", default=None, help="Vault directory path.")
    p_check.add_argument("--all", action="store_true", help="Run all available checks.")

    p_doctor = subparsers.add_parser(
        "doctor", help="Diagnose vault configuration and permissions."
    )
    p_doctor.add_argument("--path", default=None, help="Vault directory path.")

    p_copy = subparsers.add_parser(
        "copy", help="Copy an entry's field value to the clipboard."
    )
    p_copy.add_argument("--path", default=None, help="Vault directory path.")
    p_copy.add_argument("id", help="Entry id.")
    p_copy.add_argument(
        "--field", required=True, help="Field whose value to copy to the clipboard."
    )

    p_completion = subparsers.add_parser(
        "completion", help="Generate shell completion scripts."
    )
    p_completion.add_argument(
        "shell",
        choices=["bash", "zsh", "powershell"],
        help="Shell to generate completion for.",
    )

    p_config = subparsers.add_parser(
        "config", help="Manage app-level configuration (e.g. default vault)."
    )
    p_config_sub = p_config.add_subparsers(dest="config_command")

    p_config_show = p_config_sub.add_parser(
        "show", help="Print the configured value for a config key."
    )
    p_config_show.add_argument(
        "key", nargs="?", help="Config key (e.g. default-vault)."
    )

    p_config_set = p_config_sub.add_parser(
        "set", help="Store <key> = <value> in app config."
    )
    p_config_set.add_argument("key", help="Config key (e.g. default-vault).")
    p_config_set.add_argument("value", nargs="?", help="Value to store.")

    p_config_unset = p_config_sub.add_parser(
        "unset", help="Remove a config key. Missing key is not an error."
    )
    p_config_unset.add_argument(
        "key", nargs="?", help="Config key (e.g. default-vault)."
    )

    p_config_sub.add_parser("list", help="List all configured keys and values.")

    p_keyring = subparsers.add_parser(
        "keyring", help="Manage vault unlock key in OS keyring."
    )
    p_keyring_sub = p_keyring.add_subparsers(dest="keyring_command")

    p_keyring_store = p_keyring_sub.add_parser(
        "store", help="Store the vault's derived unlock key in the keyring."
    )
    p_keyring_store.add_argument(
        "--path", default=None, help="Vault directory path (default: default vault)."
    )

    p_keyring_clear = p_keyring_sub.add_parser(
        "clear", help="Remove the vault's unlock key from the keyring."
    )
    p_keyring_clear.add_argument(
        "--path", default=None, help="Vault directory path (default: default vault)."
    )

    p_keyring_show = p_keyring_sub.add_parser(
        "show", help="Report whether an unlock key is stored for the vault."
    )
    p_keyring_show.add_argument(
        "--path", default=None, help="Vault directory path (default: default vault)."
    )

    _build_backup_parser(subparsers)

    from cipherbox.cli.export import _build_parser as _build_export_parser
    from cipherbox.cli.import_ import _build_parser as _build_import_parser

    _build_export_parser(subparsers)
    _build_import_parser(subparsers)

    from cipherbox.cli.env import _build_parser as _build_env_parser

    _build_env_parser(subparsers)

    return parser


def _repo(args) -> VaultRepository:
    """Open the vault, resolving its decryption key when encrypted.

    ``init`` is excluded (it creates the vault). ``password change`` manages
    its own unlock flow, so it must not be auto-unlocked here. For all other
    commands on an encrypted vault, the key is resolved via ``unlock_repo``:
    OS keyring -> ``VAULT_PASSWORD`` env var -> hidden ``getpass`` prompt.
    """
    vault_path = resolve_vault_dir(getattr(args, "path", None))

    if args.command in ("init", "password"):
        return VaultRepository(vault_path)

    return unlock_repo(vault_path)


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
        if args.command == "get":
            return get_command(args, repo=_repo(args))
        if args.command == "password":
            return password_change_command(args, repo=_repo(args))
        if args.command == "generate" and args.generate_command == "password":
            return generate_password_command(args)
        if args.command == "check":
            return check_command(args)
        if args.command == "doctor":
            return doctor_command(args)
        if args.command == "copy":
            return copy_command(args, repo=_repo(args))
        if args.command == "completion":
            return completion_command(args)
        if args.command == "config":
            return config_command(args)
        if args.command == "keyring":
            return keyring_command(args)
        if args.command == "backup":
            if args.backup_command == "create":
                return backup_create_command(args)
            if args.backup_command == "list":
                return backup_list_command(args)
            if args.backup_command == "restore":
                return backup_restore_command(args)
        if args.command == "export":
            return export_command(args, repo=_repo(args))
        if args.command == "import":
            return import_command(args)
        if args.command == "env" and args.env_command == "export":
            return env_export_command(args)
        if args.command == "env" and args.env_command == "list":
            return env_list_command(args)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code

    parser.print_help()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
