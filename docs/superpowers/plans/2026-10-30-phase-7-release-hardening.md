# Phase 7 — Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make cipherbox installable, understandable, and safe enough for real personal use — reproducible release builds, installation and OS/filesystem docs, shell completion, integration tests for complete workflows, dependency auditing/linting in CI, recovery tests for corrupted files and failed imports, conflict/external-modification tests, and threat-model documentation.

**Architecture:** Mostly additive: shell completion lives in a new `src/cipherbox/cli/completion.py` module registering a `vault completion <shell>` subcommand; CI gains a GitHub Actions workflow plus lint/format/audit steps; new integration/recovery/conflict test modules live under `tests/`; docs gain install/reproducible-build/OS-filesystem pages and expanded threat-model content. No new runtime dependencies; everything is stdlib plus the existing `argon2-cffi`/`cryptography`.

**Spec:** `docs/project-spec.md` (Phase 7 section, lines 537-561)

## Global Constraints

- Language: Python; requires-python >= 3.11
- Stdlib only for CLI code — no new third-party dependencies (shell completion is pure argparse help introspection, no `argcomplete`)
- One JSON (or encrypted envelope) file per entry in the vault directory
- Entry fields: `id`, `schema_version`, `type`, `title`, `tags`, `created_at`, `updated_at`, `fields`
- Secret types: `login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery`
- Stable UUID identifiers independent of filenames; timestamps in UTC ISO 8601
- Secret field values are hidden by default; revealed only through explicit retrieval (`--field`/`--reveal`)
- Never print secret values to standard error
- Nonzero exit codes for missing entries or missing fields (EXIT_OK=0, EXIT_ERROR=1, EXIT_VALIDATION=2, EXIT_NOT_FOUND=3, EXIT_DUPLICATE=4, EXIT_CONFIRMATION=5)
- CLI-first: no application logic depends directly on `argparse` parsing (commands take `argparse.Namespace` + optional repo)
- Tests: pytest; lint/format: ruff

## Review Focus

The spec implies these input classes/failure modes that no single task's happy-path test covers; each is pinned to a task below:

1. Corrupted / malformed entry file → `vault check` reports it as an error, vault otherwise usable (Task 5)
2. Failed import leaves the vault completely unchanged (validate-before-write) (Task 5)
3. Two entry files with the same stable ID (sync conflict) → detected, neither silently dropped (Task 6)
4. External modification of an entry file while the vault is in use → surface as conflict or error, not silent corruption (Task 6)
5. Secret value never reaches stderr on any explicit retrieval path (Tasks 4, 5, 6)
6. Encrypted vault end-to-end flow through docs-only commands: init → add → search/retrieve → export → backup → restore (Task 4)
7. Shell completion emits a valid script for each supported shell without crashing (Task 1)

---

### Task 1: Shell completion — `vault completion <shell>`

**Files:**
- Create: `src/cipherbox/cli/completion.py`
- Modify: `src/cipherbox/__main__.py` (register `completion` subcommand)
- Test: `tests/test_cli_completion.py`

**Interfaces:**
- Consumes: `argparse.ArgumentParser` (the parser built by `build_parser()`), `sys`
- Produces:
  - `completion_command(args: argparse.Namespace) -> int` — `vault completion <shell>` where `<shell>` ∈ {`bash`, `zsh`, `powershell`}; prints a shell completion script to stdout that completes `vault` subcommands and their options; exit 0 on known shell, nonzero with stderr message on unknown shell. `__main__.py` registers a `completion` subparser (positional `shell`) and dispatches to `completion_command`.

- [ ] **Step 1: Write the failing test** `tests/test_cli_completion.py` covering:
  - `vault completion bash` exits 0 and emits a script containing `vault` subcommand names (`init`, `add`, `list`, `search`, `show`, `get`, `edit`, `delete`, `backup`, `export`, `import`, `env`, `check`, `doctor`, `copy`, `generate`, `password`, `completion`)
  - `vault completion zsh` exits 0 and emits a script
  - `vault completion powershell` exits 0 and emits a script
  - `vault completion nosuchshell` exits nonzero and names the problem on stderr

```python
def test_completion_bash_exits_zero_and_mentions_subcommands(tmp_path, capsys):
    from cipherbox.cli.completion import completion_command
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


def test_completion_unknown_shell_errors(capsys):
    from cipherbox.cli.completion import completion_command
    import argparse

    code = completion_command(argparse.Namespace(shell="fish"))
    assert code != 0
    err = capsys.readouterr().err
    assert "fish" in err.lower() or "unknown" in err.lower()
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_cli_completion.py -v` → FAIL with import/name errors.
- [ ] **Step 3: Implement `cli/completion.py`** — build completion scripts from `build_parser()`; register `completion` subcommand in `__main__.py`.
- [ ] **Step 4: Run test to verify it passes** — `pytest tests/test_cli_completion.py -v` → PASS.
- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/cli/completion.py src/cipherbox/__main__.py tests/test_cli_completion.py
git commit -m "feat: vault completion command for shell completion"
```

---

### Task 2: CI workflows + reproducible release builds

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docs/release.md` (reproducible release builds + install instructions)
- Modify: `docs/user/getting-started.md` (install section)
- Test: none new (CI is verified by pushing; the workflow file is validated by running it locally where possible)

**Interfaces:** None new. Consumes existing `pyproject.toml`, `requirements.txt`, pytest, ruff.

- [ ] **Step 1: Write `.github/workflows/ci.yml`** — runs on push/PR to main: checkout, set up Python 3.11, install `.[dev]`-equivalent (pytest, ruff), run `python -m pytest`, run `ruff check`, run `ruff format --check`, build sdist + wheel (`python -m build` if available, else document the command), and a dependency-audit step (`pip install -r requirements.txt` + `pip audit` allowed to fail with a note).
- [ ] **Step 2: Write `docs/release.md`** — reproducible release build steps (`python -m pip install build`, `python -m build --sdist --wheel`, inspect artifacts), install instructions (`pip install cipherbox-py` or `pip install -e .` from source), and the `vault` command entry point.
- [ ] **Step 3: Update getting-started install** — point at `docs/release.md` for release installs, keep editable install for development.
- [ ] **Step 4: Verify workflow syntax** — run `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` to confirm valid YAML (if PyYAML available) otherwise inspect by eye.
- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml docs/release.md docs/user/getting-started.md
git commit -m "feat: CI workflows and reproducible release build docs"
```

---

### Task 3: Dependency auditing and standard Python linting

**Files:**
- Modify: `.github/workflows/ci.yml` (add lint/format/audit steps if not in Task 2 — otherwise this task confirms them)
- Create: `scripts/audit-deps.py` (optional helper listing installed packages and their versions for the audit record)
- Test: none

**Interfaces:** None new.

- [ ] **Step 1: Add/confirm CI lint step** — `ruff check` and `ruff format --check` run on every push/PR, failing the build on violations.
- [ ] **Step 2: Add/confirm dependency audit step** — install `requirements.txt`, run `pip audit` (continue-on-error, record results), and `pip list --outdated` informational.
- [ ] **Step 3: Run lint locally** — `ruff check` and `ruff format --check` both clean on the working tree.
- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml scripts/audit-deps.py
git commit -m "feat: dependency auditing and linting in CI"
```

---

### Task 4: Integration tests — complete user workflows

**Files:**
- Create: `tests/test_e2e_phase7_workflows.py`
- Test: `tests/test_e2e_phase7_workflows.py`

**Interfaces:**
- Consumes: `cipherbox.__main__:main`, `VaultRepository`, `Entry`, `VaultKeyManager`/`derive_key`/`save_vault_crypto` (for seeding encrypted vaults), `getpass` monkeypatching.
- Produces: end-to-end tests exercising the full acceptance-criteria flow through the CLI.

- [ ] **Step 1: Write the failing test** `tests/test_e2e_phase7_workflows.py` covering:
  - Plaintext workflow: `init` → `add` (login entry) → `list` shows it → `get --field password` returns value → `search` finds it → `export` writes JSON → `backup create` → `restore` recovers.
  - Encrypted workflow: seed an encrypted vault (as in `test_e2e_crypto.py`), then with the password mocked: `get --field password` returns the value, `search` finds it, `export` writes JSON (plaintext export of decrypted values), `backup create` + `restore` recovers entries.
  - Secret values never appear on stderr in any of the above.
  - `vault check --all` exits 0 on a healthy vault.

```python
def test_e2e_plaintext_full_workflow(tmp_path, capsys):
    vault_dir = tmp_path / "vault"
    assert main(["init", "--path", str(vault_dir), "--confirm"]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "add",
                "--path",
                str(vault_dir),
                "--type",
                "login",
                "--title",
                "github",
                "--field",
                "username=alice",
                "--field",
                "password=s3cret",
            ]
        )
        == 0
    )
    capsys.readouterr()
    code = main(
        ["get", "--path", str(vault_dir), ...]
    )  # id discovered from list output
    ...
```

(Exact id handling: capture `list --output json` to read the created id.)

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_e2e_phase7_workflows.py -v` → FAIL (imports/undefined behavior).
- [ ] **Step 3: Verify against existing commands** — all commands used already exist (init, add, list, get, search, export, backup create/restore, check); no production code changes needed; confirm the test drives them correctly.
- [ ] **Step 4: Run test to verify it passes** — `pytest tests/test_e2e_phase7_workflows.py -v` → PASS.
- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e_phase7_workflows.py
git commit -m "feat: integration tests for complete user workflows"
```

---

### Task 5: Recovery tests — corrupted files and failed imports

**Files:**
- Create: `tests/test_recovery.py`
- Test: `tests/test_recovery.py`

**Interfaces:**
- Consumes: `VaultRepository`, `check_command`, `import_command`, `entry_from_dict`, `validate_entry`, `MalformedFileError`, `InvalidEntryError`.

- [ ] **Step 1: Write the failing test** `tests/test_recovery.py` covering:
  - A malformed (invalid JSON) entry file: `vault check --all` reports it as an error and exits nonzero; valid entries still list.
  - A failed import (invalid schema, e.g. unknown type or missing title) leaves the vault unchanged: entry count before == after, no new files.
  - A failed import reports the validation error on stderr and exits nonzero.
  - Secret values never appear on stderr during these operations.

```python
def test_recovery_malformed_entry_reported_as_error(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))
    (tmp_path / "entries" / "broken.json").write_text(
        "{not valid json", encoding="utf-8"
    )
    code = check_command(_args(path=str(tmp_path)))
    assert code != 0
    err = capsys.readouterr().err
    assert "broken" in err.lower() or "malformed" in err.lower()
    # valid entry still listed
    assert repo.get("id-1") is not None


def test_recovery_failed_import_leaves_vault_unchanged(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))
    before = list(tmp_path.glob("entries/*.json"))
    bad = tmp_path / "bad-import.json"
    bad.write_text(
        json.dumps({"entries": [{"id": "x", "type": "nope", "title": ""}]}),
        encoding="utf-8",
    )
    code = import_command(
        argparse.Namespace(
            file=str(bad), path=str(tmp_path), policy="skip", dry_run=False
        )
    )
    assert code != 0
    after = list(tmp_path.glob("entries/*.json"))
    assert before == after
    err = capsys.readouterr().err
    assert "s3cret" not in err
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_recovery.py -v` → FAIL.
- [ ] **Step 3: Verify existing behavior** — `check_command` already reports malformed files as errors; `import_command` already validates-before-write; confirm both behave as the tests assert (no production change unless a gap is found).
- [ ] **Step 4: Run test to verify it passes** — `pytest tests/test_recovery.py -v` → PASS.
- [ ] **Step 5: Commit**

```bash
git add tests/test_recovery.py
git commit -m "feat: recovery tests for corrupted files and failed imports"
```

---

### Task 6: External modification and conflicting file copy tests

**Files:**
- Create: `tests/test_conflicts.py`
- Test: `tests/test_conflicts.py`

**Interfaces:**
- Consumes: `VaultRepository`, `list`, `detect_conflicts`, `ConflictError`, `MissingEntryError`.

- [ ] **Step 1: Write the failing test** `tests/test_conflicts.py` covering:
  - Two entry files with the same stable ID under different filenames → `VaultRepository.list()` raises `ConflictError` naming both files; neither copy dropped.
  - `detect_conflicts()` returns `{"id", "file1", "file2"}` dicts without raising.
  - External modification of an entry file (rewrite its JSON on disk) → a subsequent `get`/`list` reflects the modified content or surfaces a clear error; no silent corruption.
  - Secret values never appear on stderr.

```python
def test_conflict_duplicate_ids_across_files(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github"))
    dup = tmp_path / "entries" / "other.json"
    dup.write_text(json.dumps({...same id "id-1"...}), encoding="utf-8")
    try:
        repo.list()
        assert False, "expected ConflictError"
    except ConflictError as exc:
        assert "id-1" in str(exc)
    conf = repo.detect_conflicts()
    assert any(c["id"] == "id-1" for c in conf)

def test_external_modification_surfaced(tmp_path, capsys):
    repo = VaultRepository(tmp_path)
    repo.init(confirm=True)
    repo.add(_make_entry("id-1", "github", fields={"password": "s3cret"}))
    # External process rewrites the entry file.
    entry_file = tmp_path / "entries" / "id-1.json"
    entry_file.write_text(json.dumps({...modified title...}), encoding="utf-8")
    entry = repo.get("id-1")
    assert entry.title == "externally modified"
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_conflicts.py -v` → FAIL.
- [ ] **Step 3: Verify existing behavior** — `list()` already raises `ConflictError` on duplicate IDs; `detect_conflicts()` already reports them; external modification re-reads from disk on each `list`/`get` call (no stale cache), so the test should pass against existing code. Confirm no production change needed.
- [ ] **Step 4: Run test to verify it passes** — `pytest tests/test_conflicts.py -v` → PASS.
- [ ] **Step 5: Commit**

```bash
git add tests/test_conflicts.py
git commit -m "feat: conflict and external-modification tests"
```

---

### Task 7: Documentation — install, reproducible builds, OS/filesystems, vault lifecycle

**Files:**
- Create: `docs/release.md` (reproducible release builds + install instructions) — shared with Task 2; write here if Task 2 didn't create it
- Create: `docs/user/os-filesystems.md` (supported operating systems and filesystems)
- Modify: `docs/user/getting-started.md` (install + lifecycle overview)
- Modify: `docs/user/commands.md` (add migration/password change if gaps; mostly already current)

**Interfaces:** None new.

- [ ] **Step 1: Write `docs/release.md`** — install from PyPI (`pip install cipherbox-py`), install from source (`git clone`, `pip install -e .`), `vault` entry point, reproducible release builds (`python -m build --sdist --wheel`, inspect artifacts, hash/sign).
- [ ] **Step 2: Write `docs/user/os-filesystems.md`** — supported OSes (Windows, macOS, Linux), default vault dir per platform, filesystem notes (local disk; network/FUSE/S3-like mounts not recommended for concurrent writers; one writer at a time).
- [ ] **Step 3: Update getting-started.md** — add a "vault lifecycle" section: init, encryption at rest, `vault password change`, `vault backup`/`vault restore`, migration (export → new vault → import).
- [ ] **Step 4: Commit**

```bash
git add docs/release.md docs/user/os-filesystems.md docs/user/getting-started.md docs/user/commands.md
git commit -m "docs: install, reproducible builds, OS/filesystems, vault lifecycle"
```

---

### Task 8: Documentation — threat-model limitations

**Files:**
- Modify: `docs/user/security.md` (expand threat-model limitations)

**Interfaces:** None new.

- [ ] **Step 1: Expand `docs/user/security.md` threat-model section** — add:
  - Malware running under your user account can read the vault directory, capture the master password at the getpass prompt, read terminal history/clipboard, and access decrypted secrets in memory while a command runs; encryption at rest does not protect against a compromised host.
  - Exposure of explicitly retrieved secrets: `vault show --reveal`, `vault get`, `vault copy` print/copy values that linger in terminal scrollback, shell history, logs, and clipboard managers; treat retrieved values as secrets once on screen.
  - Exported `.env`/JSON files store plaintext; never commit to version control.
- [ ] **Step 2: Commit**

```bash
git add docs/user/security.md
git commit -m "docs: expand threat-model limitations"
```

---

### Task 9: Full suite, lint, format, docs sync, final commit

**Files:**
- Test: run `python -m pytest` (full suite)
- Modify: `README.md` (sync to phase 7: roadmap, install, docs pointers)
- Modify: `docs/user/index.md` (phase status + doc index)
- Modify: `CLAUDE.md` (phase status line)

**Interfaces:** None new. Consumes everything from Tasks 1–8.

- [ ] **Step 1: Run full test suite** — `python -m pytest -v` → all pass.
- [ ] **Step 2: Run lint and format** — `ruff check` clean; `ruff format --check` clean (apply `ruff format` if needed).
- [ ] **Step 3: Sync README.md** — roadmap marks phase 7 complete, install section points to `docs/release.md`, add pointer to shell completion (`vault completion <shell>`), threat model pointer.
- [ ] **Step 4: Sync docs/user/index.md** — phase status and document index.
- [ ] **Step 5: Sync CLAUDE.md** — phase 7 complete line.
- [ ] **Step 6: Commit**

```bash
git add README.md docs/user/index.md CLAUDE.md
git commit -m "feat: phase 7 release hardening complete"
```

---

## Self-review against spec

1. **Spec coverage:**
   - Installation instructions and reproducible release builds: Task 2 (`docs/release.md`, CI), Task 7 (`docs/release.md`, getting-started). ✓
   - Document vault init, encryption, password changes, backup, restore, migration: Task 7 (getting-started lifecycle), README already covers init/backup/restore/password change. ✓
   - Document supported operating systems and filesystems: Task 7 (`docs/user/os-filesystems.md`). ✓
   - Shell completion where practical: Task 1 (`vault completion bash|zsh|powershell`). ✓
   - Integration tests covering complete user workflows: Task 4 (`tests/test_e2e_phase7_workflows.py`). ✓
   - Dependency auditing and standard Python linting: Task 3 (CI lint + audit steps). ✓
   - Test recovery from corrupted files and failed imports: Task 5 (`tests/test_recovery.py`). ✓
   - Test external modifications and conflicting file copies: Task 6 (`tests/test_conflicts.py`). ✓
   - Document threat-model limitations (malware under user account, exposure of explicitly retrieved secrets): Task 8 (`docs/user/security.md`). ✓
   - Acceptance criterion (install → init → create encrypted entries → search/retrieve → sync → export → restore using only docs): Tasks 2, 4, 7 cover install + docs + end-to-end encrypted flow. ✓

2. **Step scan:** Every step lets the implementer write exactly one reasonable thing; no line decides nothing; no function body duplicates what the signature and tests already determine.

3. **Type consistency:** `completion_command(args: argparse.Namespace) -> int` follows the existing command pattern. Test helpers (`_args`, `_make_entry`) mirror existing test-file conventions. Recovery/conflict tests reuse `VaultRepository`, `check_command`, `import_command`, `ConflictError` exactly as defined in existing modules.

4. **Review Focus:** Each of the seven listed input classes/failure modes has a test pinned to Tasks 1, 4, 5, 6 (malformed entry check error, failed-import unchanged, duplicate-ID conflict, external modification surfaced, no secret on stderr, encrypted end-to-end, completion emits scripts).

5. **Proportion:** Plan is concise relative to the Phase 7 spec; code blocks appear only where tests/signatures do not determine the body (completion script generation). Documentation and CI tasks carry the bulk of the phase, matching the spec's release-hardening focus.

---

**Plan complete and saved to `docs/superpowers/plans/2026-10-30-phase-7-release-hardening.md`. Please review the plan. Does it capture what you want?**

**Execution method already supplied:** native (the user chose "go with native mode" for phase 6 and said "let's do phase 7", continuing the same inline/TDD approach). I will implement every task myself in this session, TDD, then one final whole-branch review.
