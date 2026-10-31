"""``vault keyring store|clear|show``: persist vault unlock key in OS keyring.

Stores the *derived* AES-256 key (never the master password) in the OS
credential store, keyed by vault path. Opt-in: nothing is stored until the
user runs ``vault keyring store``.
"""

from __future__ import annotations

import argparse
import sys

from cipherbox.config.paths import resolve_vault_dir
from cipherbox.crypto.keyring import KeyringStore
from cipherbox.crypto.vault import (
    VaultKeyManager,
    load_vault_crypto,
    prompt_password,
)
from cipherbox.errors import EXIT_NOT_FOUND, VaultError


def _build_parser(subparsers) -> None:
    p_keyring = subparsers.add_parser(
        "keyring", help="Manage vault unlock key in OS keyring."
    )
    p_keyring_sub = p_keyring.add_subparsers(dest="keyring_command")

    p_store = p_keyring_sub.add_parser(
        "store", help="Store the vault's derived unlock key in the keyring."
    )
    p_store.add_argument(
        "--path", default=None, help="Vault directory path (default: default vault)."
    )

    p_clear = p_keyring_sub.add_parser(
        "clear", help="Remove the vault's unlock key from the keyring."
    )
    p_clear.add_argument(
        "--path", default=None, help="Vault directory path (default: default vault)."
    )

    p_show = p_keyring_sub.add_parser(
        "show", help="Report whether an unlock key is stored for the vault."
    )
    p_show.add_argument(
        "--path", default=None, help="Vault directory path (default: default vault)."
    )


def keyring_command(args: argparse.Namespace) -> int:
    """Run the ``vault keyring`` subcommand."""
    command = getattr(args, "keyring_command", None)
    if command is None:
        print("error: missing subcommand (store|clear|show)", file=sys.stderr)
        return 2

    vault_path = resolve_vault_dir(getattr(args, "path", None))
    store = KeyringStore()

    if command == "store":
        # Confirm the vault is encrypted and the password is correct by
        # unlocking it, then cache the derived key.
        try:
            meta = load_vault_crypto(vault_path)
        except FileNotFoundError:
            print("error: vault is not initialized", file=sys.stderr)
            return 1
        if not meta.get("encrypted"):
            print("error: vault is not encrypted", file=sys.stderr)
            return 1

        import base64

        from cipherbox.crypto.kdf import kdf_params_from_dict

        salt = base64.b64decode(meta["salt"])
        params = kdf_params_from_dict(meta["kdf_params"])

        password = prompt_password("Enter master password: ")
        mgr = VaultKeyManager()
        try:
            key = mgr.unlock(password, salt, params)
        except VaultError as exc:
            print(f"error: failed to unlock vault: {exc}", file=sys.stderr)
            return EXIT_NOT_FOUND

        store.store(vault_path, key)
        print(f"Stored unlock key for vault at {vault_path}")
        return 0

    if command == "clear":
        store.erase(vault_path)
        print(f"Cleared unlock key for vault at {vault_path}")
        return 0

    if command == "show":
        cached = store.get(vault_path)
        if cached is None:
            print(f"No unlock key stored for vault at {vault_path}")
        else:
            print(f"Unlock key stored for vault at {vault_path}")
        return 0

    print(f"error: unknown keyring subcommand '{command}'", file=sys.stderr)
    return 2
