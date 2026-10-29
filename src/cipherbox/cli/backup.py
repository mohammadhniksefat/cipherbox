"""`vault backup` and `vault restore` commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cipherbox.backup import (
    create_backup,
    default_backup_dir,
    list_backups,
    restore_backup,
    validate_backup,
)
from cipherbox.errors import VaultError


def _build_parser(subparsers) -> None:
    p_backup = subparsers.add_parser("backup", help="Backup and restore the vault.")
    backup_sub = p_backup.add_subparsers(dest="backup_command")

    p_create = backup_sub.add_parser("create", help="Create a vault backup.")
    p_create.add_argument("--path", default=None, help="Vault directory path.")
    p_create.add_argument(
        "--backup-dir",
        default=None,
        help="Directory to store backups (default: <vault>-backups sibling).",
    )

    p_list = backup_sub.add_parser("list", help="List available vault backups.")
    p_list.add_argument("--path", default=None, help="Vault directory path.")
    p_list.add_argument(
        "--backup-dir",
        default=None,
        help="Directory to read backups from.",
    )

    p_restore = backup_sub.add_parser("restore", help="Restore a vault backup.")
    p_restore.add_argument("backup_id", help="Backup id to restore.")
    p_restore.add_argument("--path", default=None, help="Vault directory path.")
    p_restore.add_argument(
        "--backup-dir",
        default=None,
        help="Directory to read backups from.",
    )
    p_restore.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report what would be restored without writing.",
    )


def backup_create_command(args: argparse.Namespace) -> int:
    from cipherbox.config.paths import default_vault_dir

    vault_path = Path(getattr(args, "path", None) or default_vault_dir())
    try:
        backup_id = create_backup(
            vault_path, backup_dir=getattr(args, "backup_dir", None)
        )
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 - surface backup errors as CLI errors
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(backup_id)
    return 0


def backup_list_command(args: argparse.Namespace) -> int:
    from cipherbox.config.paths import default_vault_dir

    vault_path = Path(getattr(args, "path", None) or default_vault_dir())
    backup_dir = getattr(args, "backup_dir", None)
    if backup_dir is None:
        backup_dir = default_backup_dir(vault_path)
    try:
        backups = list_backups(backup_dir=backup_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not backups:
        print("(no backups)")
        return 0
    for b in backups:
        print(f"{b['id']}  {b['created_at']}  entries={b.get('entry_count')}")
    return 0


def backup_restore_command(args: argparse.Namespace) -> int:
    from cipherbox.config.paths import default_vault_dir

    vault_path = Path(getattr(args, "path", None) or default_vault_dir())
    backup_dir = getattr(args, "backup_dir", None)
    if backup_dir is None:
        backup_dir = default_backup_dir(vault_path)
    try:
        if not validate_backup(args.backup_id, backup_dir=backup_dir):
            print(f"error: backup {args.backup_id} failed validation", file=sys.stderr)
            return 1
        restore_backup(
            args.backup_id,
            vault_path,
            backup_dir=backup_dir,
            dry_run=getattr(args, "dry_run", False),
        )
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "dry_run", False):
        print(f"Would restore backup {args.backup_id} into {vault_path}")
    else:
        print(f"Restored backup {args.backup_id} into {vault_path}")
    return 0
