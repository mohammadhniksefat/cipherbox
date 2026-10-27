"""`vault add` command implementation."""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone

from cipherbox.domain.entry import Entry, entry_from_dict, validate_entry
from cipherbox.domain.schema import SECRET_TYPES, SCHEMA_VERSION
from cipherbox.errors import InvalidEntryError, VaultError
from cipherbox.storage.repository import VaultRepository


def _parse_fields(field_values: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in field_values:
        if "=" not in item:
            continue
        key, _, value = item.partition("=")
        fields[key.strip()] = value.strip()
    return fields


def _prompt_field(key: str) -> str:
    return input(f"{key}: ")


def add_command(args: argparse.Namespace, repo: VaultRepository | None = None) -> int:
    """Add a new entry to the vault.

    If ``repo`` is not provided, a new repository is opened at the default
    vault location (used by the CLI entry point).
    """
    if repo is None:
        from cipherbox.config.paths import default_vault_dir

        repo = VaultRepository(default_vault_dir())

    if args.type not in SECRET_TYPES:
        print(f"error: unknown secret type {args.type!r}", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    fields = _parse_fields(getattr(args, "field", []) or [])

    # Only prompt interactively when no fields were supplied on the command line.
    if not fields:
        while True:
            key = _prompt_field("field name (blank to finish)")
            if not key.strip():
                break
            value = _prompt_field(f"value for {key}")
            fields[key.strip()] = value.strip()

    entry = Entry(
        id=str(uuid.uuid4()),
        schema_version=SCHEMA_VERSION,
        type=args.type,
        title=args.title,
        tags=[],
        created_at=now,
        updated_at=now,
        fields=fields,
    )
    try:
        validate_entry(entry)
        repo.add(entry)
    except (InvalidEntryError, VaultError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 1)
    print(f"Added entry {entry.id} ({args.title})")
    return 0
