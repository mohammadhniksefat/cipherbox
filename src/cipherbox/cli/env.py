"""`vault env export` command: export project-tagged entries to a `.env` file.

Selects entries whose tags contain <project> (explicit selection only --
unrelated secrets are never exported). Writes KEY=VALUE lines with escaped
values. Warns that .env is plaintext, and refuses to overwrite an existing
output file unless --confirm.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from cipherbox.storage.repository import VaultRepository

_INVALID_ENV_KEY = re.compile(r"[^A-Za-z0-9_]")
_NOT_FIRST_CHAR = re.compile(r"^[^A-Za-z_]")


def _env_key(field_name: str) -> str:
    """Sanitize a field name into a valid environment variable key."""
    key = field_name.upper()
    if not key:
        key = "EMPTY"
    key = _INVALID_ENV_KEY.sub("_", key)
    if _NOT_FIRST_CHAR.match(key):
        key = "_" + key
    return key


def _env_value(value: str) -> str:
    """Escape a value for a .env file (double-quoted, inner quotes escaped)."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _build_parser(subparsers) -> None:
    p_env = subparsers.add_parser("env", help="Environment management.")
    env_sub = p_env.add_subparsers(dest="env_command")

    p_export = env_sub.add_parser(
        "export", help="Export project-tagged entries to a .env file."
    )
    p_export.add_argument("project", help="Project tag to select entries for.")
    p_export.add_argument("--path", default=None, help="Vault directory path.")
    p_export.add_argument(
        "--output",
        required=True,
        help="Output .env file path.",
    )
    p_export.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm overwrite of an existing output file.",
    )

    p_list = env_sub.add_parser(
        "list", help="List project-tagged entries with values redacted."
    )
    p_list.add_argument("project", help="Project tag to select entries for.")
    p_list.add_argument("--path", default=None, help="Vault directory path.")


def env_export_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """Export entries tagged with <project> to a .env file."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        vault_path = Path(getattr(args, "path", None) or default_vault_dir())
        repo = VaultRepository(vault_path)

    project = args.project
    output = Path(args.output)

    # Select only entries explicitly tagged with the project.
    entries = [e for e in repo.list() if project in e.tags]

    # Plaintext warning: .env files store secret values in plaintext.
    print(
        "warning: .env export writes secret values in plaintext; "
        "protect the output file like a secret and never commit it to version control",
        file=sys.stderr,
    )

    if output.exists() and not getattr(args, "confirm", False):
        print(
            f"error: output file {output} already exists; pass --confirm to overwrite",
            file=sys.stderr,
        )
        return 1

    lines = []
    for entry in entries:
        for key, value in entry.fields.items():
            lines.append(f"{_env_key(key)}={_env_value(value)}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    print(f"Exported {len(entries)} entries tagged {project!r} to {output}")
    return 0


def env_list_command(
    args: argparse.Namespace, repo: VaultRepository | None = None
) -> int:
    """List entries tagged with <project>, with field values redacted."""
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        vault_path = Path(getattr(args, "path", None) or default_vault_dir())
        repo = VaultRepository(vault_path)

    project = args.project
    entries = [e for e in repo.list() if project in e.tags]

    if not entries:
        print("(no entries)")
        return 0

    for entry in entries:
        print(f"{entry.id}\t{entry.type}\t{entry.title}")
        if entry.fields:
            for key in sorted(entry.fields):
                print(f"\t{key}: <redacted>")
        else:
            print("\tfields: (none)")
    return 0
