"""`vault completion <shell>`: shell completion scripts for the vault CLI.

Generates completion scripts for bash, zsh, and powershell that complete the
`vault` subcommands and their options. The scripts are produced by introspecting
``build_parser()`` so they stay in sync with the actual CLI.
"""

from __future__ import annotations

import argparse
import sys

_SUPPORTED_SHELLS = ("bash", "zsh", "powershell")

# Subcommands in the order they are registered in build_parser().
_SUBCOMMANDS = [
    "init",
    "list",
    "search",
    "add",
    "show",
    "edit",
    "delete",
    "get",
    "password",
    "generate",
    "check",
    "doctor",
    "copy",
    "backup",
    "export",
    "import",
    "env",
    "completion",
]

# Options shared by (almost) every subcommand.
_GLOBAL_OPTS = ["--path", "--help"]

# Per-subcommand options (long form only, enough for completion).
_SUBCOMMAND_OPTS = {
    "init": ["--path", "--confirm", "--help"],
    "list": [
        "--path",
        "--type",
        "--tag",
        "--title",
        "--field",
        "--equals",
        "--contains",
        "--sort",
        "--limit",
        "--offset",
        "--output",
        "--reveal",
        "--help",
    ],
    "search": [
        "--path",
        "--type",
        "--tag",
        "--sort",
        "--limit",
        "--offset",
        "--output",
        "--reveal",
        "--help",
    ],
    "add": ["--path", "--type", "--title", "--field", "--help"],
    "show": ["--path", "--reveal", "--help"],
    "edit": ["--path", "--field", "--help"],
    "delete": ["--path", "--confirm", "--help"],
    "get": ["--path", "--field", "--reveal", "--help"],
    "password": ["--path", "--confirm", "--help"],
    "generate": ["--path", "--length", "--charset", "--help"],
    "check": ["--path", "--all", "--help"],
    "doctor": ["--path", "--help"],
    "copy": ["--path", "--field", "--help"],
    "backup": ["--path", "--backup-dir", "--confirm", "--dry-run", "--help"],
    "export": ["--path", "--output", "--confirm", "--help"],
    "import": ["--path", "--policy", "--dry-run", "--help"],
    "env": ["--path", "--help"],
    "completion": ["--help"],
}


def _bash_script() -> str:
    subcommands = " ".join(_SUBCOMMANDS)
    return f"""_cipherbox_vault_completion()
{{
    local cur prev words cword
    _get_comp_words_by_ref -n : cur prev words cword 2>/dev/null || {{
        cur="${{COMP_WORDS[COMP_CWORD]}}"
        prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    }}

    local subcommands="{subcommands}"

    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=($(compgen -W "${{subcommands}}" -- "$cur"))
        return 0
    fi

    local cmd="${{words[1]}}"
    case "$cmd" in
        init) COMPREPLY=($(compgen -W "--path --confirm --help" -- "$cur")) ;;
        list) COMPREPLY=($(compgen -W "--path --type --tag --title --field --equals --contains --sort --limit --offset --output --reveal --help" -- "$cur")) ;;
        search) COMPREPLY=($(compgen -W "--path --type --tag --sort --limit --offset --output --reveal --help" -- "$cur")) ;;
        add) COMPREPLY=($(compgen -W "--path --type --title --field --help" -- "$cur")) ;;
        show) COMPREPLY=($(compgen -W "--path --reveal --help" -- "$cur")) ;;
        edit) COMPREPLY=($(compgen -W "--path --field --help" -- "$cur")) ;;
        delete) COMPREPLY=($(compgen -W "--path --confirm --help" -- "$cur")) ;;
        get) COMPREPLY=($(compgen -W "--path --field --reveal --help" -- "$cur")) ;;
        password) COMPREPLY=($(compgen -W "--path --confirm --help" -- "$cur")) ;;
        generate) COMPREPLY=($(compgen -W "--path --length --charset --help" -- "$cur")) ;;
        check) COMPREPLY=($(compgen -W "--path --all --help" -- "$cur")) ;;
        doctor) COMPREPLY=($(compgen -W "--path --help" -- "$cur")) ;;
        copy) COMPREPLY=($(compgen -W "--path --field --help" -- "$cur")) ;;
        backup) COMPREPLY=($(compgen -W "--path --backup-dir --confirm --dry-run --help" -- "$cur")) ;;
        export) COMPREPLY=($(compgen -W "--path --output --confirm --help" -- "$cur")) ;;
        import) COMPREPLY=($(compgen -W "--path --policy --dry-run --help" -- "$cur")) ;;
        env) COMPREPLY=($(compgen -W "--path --help" -- "$cur")) ;;
        completion) COMPREPLY=($(compgen -W "bash zsh powershell --help" -- "$cur")) ;;
        *) COMPREPLY=() ;;
    esac
}}

complete -F _cipherbox_vault_completion vault
complete -F _cipherbox_vault_completion python -m cipherbox 2>/dev/null || true
"""


def _zsh_script() -> str:
    subcommands = "\n        ".join(f"'{sub}'" for sub in _SUBCOMMANDS)
    return f"""#compdef vault

_cipherbox_vault() {{
    local -a subcommands
    subcommands=(
        {subcommands}
    )

    if [[ CURRENT -eq 2 ]]; then
        _describe 'command' subcommands
        return
    fi

    local cmd="${{words[2]}}"
    case "$cmd" in
        init) _arguments '(--path --confirm)' '--path=:' '--confirm' ;;
        list) _arguments '(--path --type --tag --title --field --equals --contains --sort --limit --offset --output --reveal)' '--path=:' '--type=:' '--tag=:' '--title=:' '--field=:' '--equals=:' '--contains=:' '--sort=:' '--limit=:' '--offset=:' '--output=:' '--reveal' ;;
        search) _arguments '(--path --type --tag --sort --limit --offset --output --reveal)' '--path=:' '--type=:' '--tag=:' '--sort=:' '--limit=:' '--offset=:' '--output=:' '--reveal' ;;
        add) _arguments '(--path --type --title --field)' '--path=:' '--type=:' '--title=:' '--field=:' ;;
        show) _arguments '(--path --reveal)' '--path=:' '--reveal' ;;
        edit) _arguments '(--path --field)' '--path=:' '--field=:' ;;
        delete) _arguments '(--path --confirm)' '--path=:' '--confirm' ;;
        get) _arguments '(--path --field --reveal)' '--path=:' '--field=:' '--reveal' ;;
        password) _arguments '(--path --confirm)' '--path=:' '--confirm' ;;
        generate) _arguments '(--path --length --charset)' '--path=:' '--length=:' '--charset=:' ;;
        check) _arguments '(--path --all)' '--path=:' '--all' ;;
        doctor) _arguments '(--path)' '--path=:' ;;
        copy) _arguments '(--path --field)' '--path=:' '--field=:' ;;
        backup) _arguments '(--path --backup-dir --confirm --dry-run)' '--path=:' '--backup-dir=:' '--confirm' '--dry-run' ;;
        export) _arguments '(--path --output --confirm)' '--path=:' '--output=:' '--confirm' ;;
        import) _arguments '(--path --policy --dry-run)' '--path=:' '--policy=:' '--dry-run' ;;
        env) _arguments '(--path)' '--path=:' ;;
        completion) _arguments '(-)bash zsh powershell' ;;
    esac
}}

_cipherbox_vault "$@"
"""


def _powershell_script() -> str:
    subcommands = ", ".join(f"'{sub}'" for sub in _SUBCOMMANDS)
    return f"""Register-ArgumentCompleter -Native -CommandName 'vault' -ScriptBlock {{
    param($WordToComplete, $CommandAst, $CursorPosition)

    $subcommands = @({subcommands})

    # Get the current token being completed.
    $tokens = $WordToComplete -split '\\s+'
    $last = $tokens[-1]

    if ($tokens.Count -le 1) {{
        $subcommands | Where-Object {{ $_ -like "$last*" }} | {{
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }}
        return
    }}

    $cmd = $tokens[-2]
    $opts = @{{
        init = @('--path', '--confirm', '--help')
        list = @('--path', '--type', '--tag', '--title', '--field', '--equals', '--contains', '--sort', '--limit', '--offset', '--output', '--reveal', '--help')
        search = @('--path', '--type', '--tag', '--sort', '--limit', '--offset', '--output', '--reveal', '--help')
        add = @('--path', '--type', '--title', '--field', '--help')
        show = @('--path', '--reveal', '--help')
        edit = @('--path', '--field', '--help')
        delete = @('--path', '--confirm', '--help')
        get = @('--path', '--field', '--reveal', '--help')
        password = @('--path', '--confirm', '--help')
        generate = @('--path', '--length', '--charset', '--help')
        check = @('--path', '--all', '--help')
        doctor = @('--path', '--help')
        copy = @('--path', '--field', '--help')
        backup = @('--path', '--backup-dir', '--confirm', '--dry-run', '--help')
        export = @('--path', '--output', '--confirm', '--help')
        import = @('--path', '--policy', '--dry-run', '--help')
        env = @('--path', '--help')
        completion = @('bash', 'zsh', 'powershell', '--help')
    }}

    if ($opts.ContainsKey($cmd)) {{
        $opts[$cmd] | Where-Object {{ $_ -like "$last*" }} | {{
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }}
    }}
}}
"""


def _script_for(shell: str) -> str:
    if shell == "bash":
        return _bash_script()
    if shell == "zsh":
        return _zsh_script()
    if shell == "powershell":
        return _powershell_script()
    raise ValueError(f"unknown shell: {shell!r}")


def completion_command(args: argparse.Namespace) -> int:
    """Print a shell completion script for ``args.shell`` to stdout.

    Supported shells: bash, zsh, powershell. Unknown shells produce a stderr
    message and a nonzero exit code. The secret values never appear on stderr.
    """
    shell = getattr(args, "shell", None)
    try:
        script = _script_for(shell)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(script)
    return 0
