"""Tests for the `vault generate password` command."""

import argparse
import string

from cipherbox.cli.generate import generate_password_command


def _args(**kwargs) -> argparse.Namespace:
    base = dict(length=32, charset="lower,digits")
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_generate_password_length_and_charset(tmp_path, capsys):
    code = generate_password_command(_args(length=32, charset="lower,digits"))
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert len(out) == 32
    assert set(out) <= set(string.ascii_lowercase + string.digits)


def test_generate_password_default_length(tmp_path, capsys):
    base = dict(charset="lower,digits")
    # length omitted on purpose: the command's default should apply.
    code = generate_password_command(argparse.Namespace(**base))
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert len(out) == 32


def test_generate_password_prints_to_stdout_not_stderr(tmp_path, capsys):
    code = generate_password_command(_args(length=16, charset="lower"))
    assert code == 0
    out = capsys.readouterr().out
    err = capsys.readouterr().err
    assert len(out.strip()) == 16
    assert err == ""
