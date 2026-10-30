"""`vault generate password` command: CSPRNG-based password generation."""

from __future__ import annotations

import argparse
import secrets
import string
import sys

_DEFAULT_LENGTH = 32

_CHARSETS = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "punctuation": string.punctuation,
}


def _build_charset(charset: str | None) -> str:
    """Resolve a comma-separated charset list to a character pool."""
    if not charset:
        return _CHARSETS["lower"] + _CHARSETS["digits"]
    pool = ""
    for part in charset.split(","):
        part = part.strip()
        if part in _CHARSETS:
            pool += _CHARSETS[part]
        else:
            print(
                f"error: unknown charset {part!r}; choose from {sorted(_CHARSETS)}",
                file=sys.stderr,
            )
            sys.exit(1)
    if not pool:
        return _CHARSETS["lower"] + _CHARSETS["digits"]
    return pool


def generate_password_command(args: argparse.Namespace) -> int:
    """Generate a password with a CSPRNG and print it to stdout.

    Never stores the generated password automatically. Exit code 1 on
    bad charset input.
    """
    length = int(getattr(args, "length", _DEFAULT_LENGTH) or _DEFAULT_LENGTH)
    charset = getattr(args, "charset", None) or "lower,digits"
    pool = _build_charset(charset)

    password = "".join(secrets.choice(pool) for _ in range(length))
    print(password)
    return 0
