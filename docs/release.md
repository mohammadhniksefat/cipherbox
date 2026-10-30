# Release builds and installation

## Install

### From PyPI (recommended for users)

```bash
pip install cipherbox
```

This provides the `vault` command:

```bash
vault --help
```

### From source (development)

```bash
git clone <repo>
cd cipherbox-py
python -m pip install -e .
```

This provides both the `vault` entry point and `python -m cipherbox`:

```bash
vault --help
python -m cipherbox --help
```

If `--path` is omitted, the default vault location is used:

- Windows: `%LOCALAPPDATA%/cipherbox-vault`
- macOS/Linux: `$XDG_DATA_HOME/cipherbox-vault` or `~/.local/share/cipherbox-vault`

## Reproducible release builds

Build from a clean checkout at a tagged commit:

```bash
python -m pip install build
python -m build --sdist --wheel --outdir dist/
```

This produces `dist/cipherbox-<version>.tar.gz` and
`dist/cipherbox-<version>-py3-none-any.whl`. Verify the artifacts before
publishing:

```bash
ls -l dist/
python -m pip install dist/cipherbox-<version>-py3-none-any.whl --force-reinstall
vault --help
```

The `vault` entry point is declared in `pyproject.toml` as
`vault = "cipherbox.__main__:main"`.

## Shell completion

Generate completion for your shell and source it:

```bash
# bash
vault completion bash > ~/.local/share/bash-completion/completions/vault

# zsh
vault completion zsh > ~/.zsh/completions/_vault

# powershell
vault completion powershell > $PROFILE
```

Then restart your shell. `vault completion <shell>` works for
`bash`, `zsh`, and `powershell`.
