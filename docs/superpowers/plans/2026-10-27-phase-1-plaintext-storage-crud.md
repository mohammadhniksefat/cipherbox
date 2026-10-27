# Phase 1 — Plaintext Storage Engine and CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 1 of cipherbox-py: a working local vault with plaintext storage, vault initialization, six secret types, and full CRUD (add, show, edit, delete) backed by one JSON file per entry.

**Architecture:** Python CLI with a thin argparse layer over a domain model (`Entry`), a JSON file repository (`VaultRepository`), and a vault path config. CLI parses args and delegates to the repository; the repository owns validation, serialization, and file I/O. No encryption in this phase — plaintext is a development prototype only.

**Tech Stack:** Python 3.11+, stdlib only (argparse, json, uuid, datetime, pathlib, dataclasses), pytest for tests, ruff for lint/format.

**Spec:** `docs/project-spec.md` (Phase 1 section)

## Global Constraints

- Language: Python (per updated spec)
- One JSON file per entry in the vault directory
- Entry fields: `id`, `schema_version`, `type`, `title`, `tags`, `created_at`, `updated_at`, `fields`
- Secret types: `login`, `api-key`, `ssh`, `secure-note`, `env`, `recovery`
- Stable UUID identifiers independent of filenames; timestamps in UTC ISO 8601
- `vault init` and `vault init --path <path>`; refuse to overwrite an existing vault without confirmation
- `show` redacts secret fields by default
- `edit` preserves ID and `created_at`
- `delete` requires confirmation unless explicitly overridden
- Validate on read and write; reject duplicate IDs and invalid schemas; detect missing files and malformed JSON; never silently overwrite an unrelated entry

## Review Focus

The spec implies these input classes/failure modes that no single task's happy-path test covers; each is pinned to a task below:

1. Re-initializing an existing vault without confirmation → refused (Task 5)
2. Duplicate entry ID on `add` → actionable error (Task 6)
3. Malformed JSON file in vault → actionable error, not a crash (Task 4)
4. Missing entry on `show`/`edit`/`delete` → actionable error (Tasks 7, 8, 9)
5. Invalid secret type → rejection at validation (Task 2)
6. Deleting one entry must not touch siblings (Task 9)
7. `edit` must preserve `id` and `created_at` (Task 8)

---

### Task 1: Project scaffolding and packaging

**Files:**
- Create: `pyproject.toml`
- Create: `src/cipherbox/__init__.py`
- Create: `src/cipherbox/__main__.py`
- Create: `src/cipherbox/errors.py`
- Modify: `CLAUDE.md` (already updated to Python references — no further change needed here)

**Interfaces:**
- Produces: `cipherbox.errors.VaultError` (base), `DuplicateIdError`, `InvalidEntryError`, `MissingEntryError`, `MalformedFileError`, `ConfirmationRequiredError`; exit codes: 0 success, 1 generic error, 2 validation, 3 not found, 4 conflict/duplicate, 5 confirmation required.

- [ ] **Step 1: Write `pyproject.toml`** with package name `cipherbox`, Python >=3.11, console script `vault = cipherbox.__main__:main`, pytest and ruff as dev dependencies.

- [ ] **Step 2: Install the package in editable mode** (`pip install -e .`) and verify `vault --help` runs.

- [ ] **Step 3: Write `errors.py`** defining the error hierarchy and exit-code constants.

- [ ] **Step 4: Write `__main__.py`** with a minimal `main(argv)` that builds the argparse parser and returns an exit code (no subcommands yet).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/cipherbox/
git commit -m "feat: project scaffolding, packaging, and error types"
```

---

### Task 2: Domain model — Entry, secret types, validation

**Files:**
- Create: `src/cipherbox/domain/__init__.py`
- Create: `src/cipherbox/domain/entry.py`
- Create: `src/cipherbox/domain/schema.py`
- Test: `tests/test_entry.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `SECRET_TYPES` frozenset, `SCHEMA_VERSION = 1`, `Entry` dataclass (`id`, `schema_version`, `type`, `title`, `tags`, `created_at`, `updated_at`, `fields`), `validate_entry(entry) -> None`, `entry_from_dict(data) -> Entry`, `entry_to_dict(entry) -> dict`.

- [ ] **Step 1: Write the failing test** `tests/test_entry.py` covering: valid entry round-trips through `to_dict`/`from_dict`; invalid type raises `InvalidEntryError`; missing required field raises; extra unknown field is preserved or rejected per schema.

```python
def test_entry_round_trip():
    e = Entry(id="...", schema_version=1, type="login", title="github", tags=["dev"], created_at="...", updated_at="...", fields={"username": "u", "password": "p"})
    assert entry_from_dict(entry_to_dict(e)) == e

def test_invalid_type_rejected():
    with pytest.raises(InvalidEntryError):
        validate_entry(Entry(..., type="not-a-type", ...))
```

- [ ] **Step 2: Run test to verify it fails** — `pytest tests/test_entry.py -v` → FAIL with name errors.

- [ ] **Step 3: Implement `schema.py`** (`SECRET_TYPES`, `SCHEMA_VERSION`, per-type field schemas) and `entry.py` (`Entry` dataclass, `validate_entry`, `entry_from_dict`, `entry_to_dict`).

- [ ] **Step 4: Run test to verify it passes** — `pytest tests/test_entry.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/domain/ tests/test_entry.py
git commit -m "feat: domain model, entry validation, and secret types"
```

---

### Task 3: Vault path configuration

**Files:**
- Create: `src/cipherbox/config/__init__.py`
- Create: `src/cipherbox/config/paths.py`
- Test: `tests/test_paths.py`

**Interfaces:**
- Produces: `VaultConfig` with `vault_dir` (Path), `config_file` (Path), `entries_dir` (Path); `default_vault_dir()` → platform config dir / cipherbox-vault; `load_config(config_file) -> VaultConfig`; `save_config(config) -> None`.

- [ ] **Step 1: Write the failing test** `tests/test_paths.py` covering: default vault dir resolution, config file read/write round-trip, entries dir derivation.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Implement `paths.py`** — `VaultConfig` dataclass, default dir logic (XDG on posix, `LOCALAPPDATA` on Windows, fallback `~/.cipherbox-vault`), JSON config persistence.

- [ ] **Step 4: Run test to verify it passes.**

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/config/ tests/test_paths.py
git commit -m "feat: vault path configuration"
```

---

### Task 4: Storage repository — JSON file CRUD

**Files:**
- Create: `src/cipherbox/storage/__init__.py`
- Create: `src/cipherbox/storage/repository.py`
- Test: `tests/test_repository.py`

**Interfaces:**
- Consumes: `Entry`, `validate_entry`, `entry_from_dict`, `entry_to_dict` (Task 2); `VaultConfig` (Task 3); error types (Task 1).
- Produces: `VaultRepository(vault_path)` with `init(confirm=False)`, `add(entry)`, `get(entry_id)`, `show(entry_id, redact=True)`, `edit(entry_id, updates)`, `delete(entry_id, confirm=False)`, `list()`; file layout `<vault>/entries/<id>.json`.

- [ ] **Step 1: Write the failing test** `tests/test_repository.py` covering: `add` then `get` round-trip with no field loss; duplicate ID raises `DuplicateIdError`; missing file raises `MissingEntryError`; malformed JSON raises `MalformedFileError`; `show` redacts fields by default but reveals with `redact=False`; deleting one entry leaves others intact.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Implement `repository.py`** — JSON per entry, atomic write (temp file + replace), validation on read/write, duplicate-ID detection on add, redaction of `fields` values in `show`.

- [ ] **Step 4: Run test to verify it passes.**

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/storage/ tests/test_repository.py
git commit -m "feat: JSON file storage repository with CRUD"
```

---

### Task 5: `vault init` command

**Files:**
- Create: `src/cipherbox/cli/__init__.py`
- Create: `src/cipherbox/cli/vault.py`
- Create: `src/cipherbox/cli/init.py`
- Test: `tests/test_cli_init.py`

**Interfaces:**
- Consumes: `VaultRepository.init` (Task 4), `VaultConfig` (Task 3).
- Produces: CLI command `vault init` and `vault init --path <path>`; creates vault dir, config, entries subdir; refuses existing vault without `--confirm`/confirmation.

- [ ] **Step 1: Write the failing test** `tests/test_cli_init.py` covering: init creates dirs and config file; re-init without confirmation returns nonzero/exits cleanly; `--path` uses custom location.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Implement `init.py`** — argparse subcommand, directory creation, confirmation prompt when vault exists, config file write.

- [ ] **Step 4: Run test to verify it passes.**

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/cli/ tests/test_cli_init.py
git commit -m "feat: vault init command"
```

---

### Task 6: `vault add` command

**Files:**
- Create: `src/cipherbox/cli/add.py`
- Test: `tests/test_cli_add.py`

**Interfaces:**
- Consumes: `VaultRepository.add` (Task 4), `Entry`/`validate_entry` (Task 2).
- Produces: `vault add <type> <title>` prompting for fields interactively (or via stdin flags); rejects duplicate ID and invalid type.

- [ ] **Step 1: Write the failing test** `tests/test_cli_add.py` covering: adding a login entry creates the file; duplicate title/ID rejected; invalid type rejected.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Implement `add.py`** — field collection per type, UUID generation, UTC timestamps, validation before write.

- [ ] **Step 4: Run test to verify it passes.**

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/cli/add.py tests/test_cli_add.py
git commit -m "feat: vault add command"
```

---

### Task 7: `vault show` command

**Files:**
- Create: `src/cipherbox/cli/show.py`
- Test: `tests/test_cli_show.py`

**Interfaces:**
- Consumes: `VaultRepository.show` (Task 4).
- Produces: `vault show <id>` prints metadata and redacted fields by default; `--reveal` shows values; missing entry → error.

- [ ] **Step 1: Write the failing test** `tests/test_cli_show.py` covering: metadata printed, field values redacted by default, `--reveal` shows values, missing entry error.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Implement `show.py`** — table output, redaction toggle, missing-entry handling.

- [ ] **Step 4: Run test to verify it passes.**

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/cli/show.py tests/test_cli_show.py
git commit -m "feat: vault show command"
```

---

### Task 8: `vault edit` command

**Files:**
- Create: `src/cipherbox/cli/edit.py`
- Test: `tests/test_cli_edit.py`

**Interfaces:**
- Consumes: `VaultRepository.edit` (Task 4).
- Produces: `vault edit <id>` updates fields without changing `id` or `created_at`; `updated_at` refreshed; missing entry → error.

- [ ] **Step 1: Write the failing test** `tests/test_cli_edit.py` covering: field updated, `id` and `created_at` preserved, `updated_at` changed, missing entry error.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Implement `edit.py`** — field update, timestamp handling, missing-entry error.

- [ ] **Step 4: Run test to verify it passes.**

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/cli/edit.py tests/test_cli_edit.py
git commit -m "feat: vault edit command"
```

---

### Task 9: `vault delete` command

**Files:**
- Create: `src/cipherbox/cli/delete.py`
- Test: `tests/test_cli_delete.py`

**Interfaces:**
- Consumes: `VaultRepository.delete` (Task 4).
- Produces: `vault delete <id>` requires confirmation unless `--confirm`; deletes only that entry's file; missing entry → error.

- [ ] **Step 1: Write the failing test** `tests/test_cli_delete.py` covering: entry file removed, sibling entries untouched, confirmation required by default, `--confirm` skips prompt, missing entry error.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Implement `delete.py`** — confirmation prompt, single-file deletion, missing-entry error.

- [ ] **Step 4: Run test to verify it passes.**

- [ ] **Step 5: Commit**

```bash
git add src/cipherbox/cli/delete.py tests/test_cli_delete.py
git commit -m "feat: vault delete command"
```

---

### Task 10: CLI wiring and end-to-end verification

**Files:**
- Modify: `src/cipherbox/__main__.py` (register all subcommands)
- Create: `tests/test_e2e_crud.py`

**Interfaces:**
- Consumes: all CLI command modules (Tasks 5–9).
- Produces: complete `vault` CLI with init/add/show/edit/delete; end-to-end test exercising CRUD through the CLI.

- [ ] **Step 1: Write the failing e2e test** `tests/test_e2e_crud.py` covering: init → add → show (redacted) → edit → show → delete → list-empty, all via CLI subprocess or invoke.

- [ ] **Step 2: Run test to verify it fails.**

- [ ] **Step 3: Wire subcommands into `__main__.py`** — register init, add, show, edit, delete under the `vault` group.

- [ ] **Step 4: Run e2e test to verify it passes.**

- [ ] **Step 5: Run full test suite** `python -m pytest -v` and `ruff check` / `ruff format --check`.

- [ ] **Step 6: Commit**

```bash
git add src/cipherbox/__main__.py tests/test_e2e_crud.py
git commit -m "feat: CLI wiring and end-to-end CRUD verification"
```

---

### Task 11: Phase 1 acceptance review

**Files:** None new.

- [ ] **Step 1: Re-read Phase 1 acceptance criteria** from `docs/project-spec.md` and confirm each is covered by a test.

- [ ] **Step 2: Run full suite** `python -m pytest -v` → all pass; `ruff check` and `ruff format --check` → clean.

- [ ] **Step 3: Commit any final fixes.**

```bash
git commit -m "chore: phase 1 acceptance and lint cleanup"
```
