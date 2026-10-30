"""Tests for the `vault completion <shell>` command."""

from cipherbox.cli.completion import completion_command


def test_completion_bash_exits_zero_and_mentions_subcommands(capsys):
    import argparse

    code = completion_command(argparse.Namespace(shell="bash"))
    assert code == 0
    out = capsys.readouterr().out
    for sub in (
        "init",
        "add",
        "list",
        "search",
        "show",
        "get",
        "edit",
        "delete",
        "backup",
        "export",
        "import",
        "env",
        "check",
        "doctor",
        "copy",
        "generate",
        "password",
        "completion",
    ):
        assert sub in out


def test_completion_zsh_exits_zero_and_emits_script(capsys):
    import argparse

    code = completion_command(argparse.Namespace(shell="zsh"))
    assert code == 0
    out = capsys.readouterr().out
    assert "vault" in out
    for sub in ("init", "add", "list", "search", "show", "get", "edit", "delete"):
        assert sub in out


def test_completion_powershell_exits_zero_and_emits_script(capsys):
    import argparse

    code = completion_command(argparse.Namespace(shell="powershell"))
    assert code == 0
    out = capsys.readouterr().out
    assert "vault" in out


def test_completion_unknown_shell_errors(capsys):
    import argparse

    code = completion_command(argparse.Namespace(shell="fish"))
    assert code != 0
    err = capsys.readouterr().err
    assert "fish" in err.lower() or "unknown" in err.lower()
