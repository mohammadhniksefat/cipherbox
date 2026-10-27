"""Application entry point for the ``vault`` CLI."""

from __future__ import annotations

import argparse
import sys

from cipherbox.errors import EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vault",
        description="Local-first secrets manager.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("init", help="Initialize a vault directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
