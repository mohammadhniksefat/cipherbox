"""``vault config show|set|unset``: app-level key-value configuration.

Manages app-level config stored outside any vault (e.g. the default vault
path), following a git-like ``config show|set|unset`` interface.
"""

from __future__ import annotations

import argparse
import sys

from cipherbox.config.app_config import load_app_config
from cipherbox.errors import EXIT_NOT_FOUND


def _build_parser(subparsers) -> None:
    p_config = subparsers.add_parser(
        "config", help="Manage app-level configuration (e.g. default vault)."
    )
    p_config_sub = p_config.add_subparsers(dest="config_command")

    p_show = p_config_sub.add_parser(
        "show", help="Print the configured value for a config key."
    )
    p_show.add_argument("key", nargs="?", help="Config key (e.g. default-vault).")

    p_set = p_config_sub.add_parser("set", help="Store <key> = <value> in app config.")
    p_set.add_argument("key", nargs="?", help="Config key (e.g. default-vault).")
    p_set.add_argument("value", nargs="?", help="Value to store.")

    p_unset = p_config_sub.add_parser(
        "unset", help="Remove a config key. Missing key is not an error."
    )
    p_unset.add_argument("key", nargs="?", help="Config key (e.g. default-vault).")


def config_command(args: argparse.Namespace) -> int:
    """Run the ``vault config`` subcommand.

    Returns an exit code (never raises SystemExit) so callers can drive it
    through ``main()``.
    """
    command = getattr(args, "config_command", None)
    if command is None:
        print("error: missing subcommand (show|set|unset)", file=sys.stderr)
        return 2

    app_config = load_app_config()

    if command == "show":
        key = getattr(args, "key", None)
        if not key:
            print("error: config show requires <key>", file=sys.stderr)
            return 2
        value = app_config.get(key)
        if value is None:
            print(f"error: config key '{key}' is not set", file=sys.stderr)
            return EXIT_NOT_FOUND
        print(value)
        return 0

    if command == "set":
        key = getattr(args, "key", None)
        value = getattr(args, "value", None)
        if not key or value is None:
            print("error: config set requires <key> <value>", file=sys.stderr)
            return 2
        app_config.set(key, value)
        print(f"set {key} = {value}")
        return 0

    if command == "unset":
        key = getattr(args, "key", None)
        if not key:
            print("error: config unset requires <key>", file=sys.stderr)
            return 2
        app_config.unset(key)
        print(f"unset {key}")
        return 0

    print(f"error: unknown config subcommand '{command}'", file=sys.stderr)
    return 2
