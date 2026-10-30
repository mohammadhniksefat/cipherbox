"""`vault check` and `vault doctor`: validation and diagnostics for a vault."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from cipherbox.config.paths import default_vault_dir, load_config
from cipherbox.domain.entry import entry_from_dict, validate_entry
from cipherbox.errors import VaultError


def _vault_dir(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "path", None) or default_vault_dir())


def check_command(args: argparse.Namespace) -> int:
    """Validate the vault: schema validity, duplicate IDs, malformed files.

    Reports warnings on stdout and errors on stderr. Never exposes decrypted
    contents or secret field values. Exit nonzero if any error is found.
    """
    vault_dir = _vault_dir(args)
    entries_dir = vault_dir / "entries"

    errors: list[str] = []
    warnings: list[str] = []

    if not vault_dir.exists():
        print(f"error: vault directory not found: {vault_dir}", file=sys.stderr)
        return 1

    # Config / encryption metadata status (never exposes secret contents).
    try:
        config = load_config(vault_dir / "config.json")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: config file is unreadable: {exc}", file=sys.stderr)
        return 1
    if config.encrypted:
        warnings.append("vault is encrypted; entry contents are not checked")
    else:
        warnings.append("vault is not encrypted")

    seen_ids: dict[str, Path] = {}
    if entries_dir.exists() and not config.encrypted:
        for path in sorted(entries_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entry = entry_from_dict(data)
                validate_entry(entry)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                errors.append(f"malformed entry file {path.name}: {exc}")
                continue
            except VaultError as exc:
                errors.append(f"invalid entry {path.name}: {exc}")
                continue
            existing = seen_ids.get(entry.id)
            if existing is not None:
                errors.append(
                    f"duplicate entry id {entry.id!r} in {path.name} and {existing.name}"
                )
            else:
                seen_ids[entry.id] = path

    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if errors:
        print("errors:")
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print(f"{len(errors)} error(s) found", file=sys.stderr)
        return 1

    print("vault check: no errors found")
    return 0


def doctor_command(args: argparse.Namespace) -> int:
    """Diagnose configuration and filesystem permission problems.

    Reports problems with clear messages. Exit nonzero on real problems.
    """
    vault_dir = _vault_dir(args)
    problems: list[str] = []

    config_file = vault_dir / "config.json"
    if not vault_dir.exists():
        print(f"error: vault directory does not exist: {vault_dir}", file=sys.stderr)
        return 1
    if not config_file.exists():
        problems.append("config.json is missing (vault may not be initialized)")
    else:
        try:
            load_config(config_file)
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"config.json is unreadable: {exc}")

    entries_dir = vault_dir / "entries"
    if entries_dir.exists():
        if not os.access(entries_dir, os.R_OK):
            problems.append(f"entries directory is not readable: {entries_dir}")
        if not os.access(entries_dir, os.W_OK):
            problems.append(f"entries directory is not writable: {entries_dir}")
    else:
        problems.append("entries directory is missing")

    if problems:
        print("doctor: problems found")
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(f"{len(problems)} problem(s)", file=sys.stderr)
        return 1

    print("doctor: vault is healthy")
    return 0
