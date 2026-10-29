"""`vault init` command implementation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cipherbox.config.paths import default_vault_dir
from cipherbox.errors import VaultError
from cipherbox.storage.repository import VaultRepository


def init_command(args: argparse.Namespace) -> int:
    vault_path = Path(args.path) if args.path else default_vault_dir()
    repo = VaultRepository(vault_path)
    try:
        repo.init(confirm=args.confirm)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    print(f"Initialized vault at {vault_path}")
    return 0
