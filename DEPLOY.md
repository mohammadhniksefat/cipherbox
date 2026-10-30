# Deploy

This document covers how to build, release, and install `cipherbox`, the local-first CLI secrets manager.

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

## Release process

`cipherbox` is versioned with git tags. A release is published by tagging a commit on `main` and pushing the tag; CI builds and publishes the artifacts.

### 1. Bump the version

Update `version` in `pyproject.toml` to the release version (e.g. `0.1.0`).

### 2. Tag and push

```bash
git tag v0.1.0
git push origin main --tags
```

Pushing the tag triggers the CI release job (if configured) which builds the sdist and wheel and publishes them to PyPI.

### 3. Build locally (to verify before publishing)

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

### 4. Publish

Publish the built artifacts to PyPI:

```bash
python -m pip install twine
python -m twine upload dist/*
```

## CI

The project uses GitHub Actions (`.github/workflows/ci.yml`) which runs on push and pull requests to `main`:

- Runs the test suite (`python -m pytest`) on Python 3.11, 3.12, and 3.13
- Lints with `ruff check` and `ruff format --check`
- Builds the sdist and wheel
- Runs a dependency audit (`pip audit`, `pip list --outdated`)

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

Then restart your shell. `vault completion <shell>` works for `bash`, `zsh`, and `powershell`.

## Support matrix

- Python: `>=3.11`
- Platforms: Windows, macOS, Linux
- Dependencies (runtime): `argon2-cffi>=23.1.0`, `cryptography>=42.0.0`
