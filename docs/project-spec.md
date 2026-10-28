# CLI Secrets Manager — Development Specification

The project should be developed in phases, with each phase delivering a usable, testable result. The goal is to build a local-first developer secrets manager that stores one encrypted JSON file per secret, with file synchronization left to the user's chosen means.

I'll use the decisions established so far:

- Interface: CLI-first.
- Language: Python as the proposed default.
- Storage: One file per secret, organized in a local vault directory.
- Encryption: Master password + Argon2id key derivation + authenticated encryption.
- Unlocking: Derive the key once per command, keep it in memory, and discard it when the process exits.
- Output: Hide secret values by default; expose them only through explicit retrieval or export operations.
- Synchronization: The application does not implement its own network synchronization; users may synchronize vault files by any means they choose.
- Recovery: Backups, imports, exports, validation, and manual conflict recovery.

The specification below is organized into implementation phases with scope, requirements, acceptance criteria, and explicit exclusions. Each phase should be independently testable before proceeding.

## Phase 0 — Project foundation and technical decisions

Deliverable: Architecture and project skeleton

### Objective

Establish the project structure and settle the storage and cryptographic contracts before implementing features.

### Requirements

- Create a Python CLI project with a clear module structure.
- Define a single application configuration location and a configurable vault directory.
- Define stable identifiers for entries, independent of filenames.
- Define a versioned schema for secret metadata and typed fields.
- Choose a maintained cryptographic library rather than implementing cryptography directly.
- Define a versioned encrypted-file envelope.
- Define consistent error types and exit codes.
- Add unit testing, formatting, linting, and CI from the beginning.

Suggested command structure:

```
vault
├── init
├── add
├── list
├── search
├── show
├── get
├── edit
├── delete
├── import
├── export
├── backup
├── restore
├── check
├── doctor
└── generate
```

Suggested module structure:

```
src/cipherbox/
├── cli/
├── config/
├── domain/
├── storage/
├── crypto/
├── services/
├── import_export/
├── backup/
└── __main__.py
```

### Acceptance criteria

- The project builds and runs on the target operating system.
- Configuration and vault paths are deterministic and documented.
- Schema and encrypted-envelope formats are documented.
- No application logic depends directly on CLI argument parsing.
- Automated tests run in CI.
### Out of scope

No actual secret management, encryption implementation, or advanced commands yet.

## Phase 1 — Plaintext storage engine and CRUD

Deliverable: Working local vault

### Objective

Implement and validate the file-based storage model before adding encryption.

Plaintext storage in this phase is strictly a development implementation, not the final default. Do not migrate real credentials into an unencrypted prototype.

### Requirements

1\. Vault initialization

```
vault init
vault init --path ./my-vault
```

Create the vault directory, configuration, and required subdirectories. Refuse to overwrite an existing vault without explicit confirmation.

2\. Secret types

Implement these initial types:

- `login`
- `api-key`
- `ssh`
- `secure-note`
- `env`
- `recovery`

Each entry has common metadata:

```
id
schema_version
type
title
tags
created_at
updated_at
fields
```

Use a UUID or equivalent stable identifier. Keep timestamps in UTC.

3\. CRUD operations

```
vault add login github
vault show github
vault edit github
vault delete github
```

- `add` creates a unique entry.
- `show` displays metadata and redacted fields by default.
- `edit` modifies an existing entry without changing its ID or creation timestamp.
- `delete` requires confirmation unless explicitly overridden.

4\. File repository

- One JSON file per entry.
- Predictable, documented directory layout.
- Validate entries when reading and writing.
- Reject duplicate IDs and invalid schemas.
- Detect missing files and malformed JSON.
- Never silently overwrite an unrelated entry.

### Acceptance criteria

- CRUD operations work end-to-end.
- Every entry can be loaded and serialized without losing fields.
- Invalid entries produce actionable errors.
- Deleting an entry affects only that entry.
- Tests cover duplicate IDs, malformed files, invalid types, and missing entries.

### Out of scope

Encryption, complex filtering, automatic conflict merging, and a background synchronization process.

## Phase 2 — Search, filtering, and developer-oriented querying

Deliverable: Useful daily CLI

### Objective

Make the vault practical for managing hundreds of heterogeneous secrets.

### Requirements

1\. Listing and filters

```
vault list
vault list --type api-key
vault list --tag development
vault list --type login --tag personal
vault list --sort updated
```

Support:

- Type filtering.
- Tag filtering.
- Exact title matching.
- Sorting by title, creation time, and update time.
- Pagination or result limits when needed.

Multiple filters should combine predictably: filters on different dimensions use AND semantics; multiple requested tags should use documented, consistent semantics.

2\. Text search

```
vault search "github"
vault search "staging" --in title,fields,tags
```

Support case-insensitive partial matching by default. Allow users to specify which fields are searchable.

3\. Field queries

```
vault list --field provider --equals openai
vault list --field hostname --contains staging
```

Field queries must work against typed entry data, not by treating arbitrary JSON serialization as the permanent query interface.

4\. Output formats

```
vault list
vault list --output json
vault list --output table
```

Machine-readable output should have a documented schema. Secret fields remain redacted unless the user explicitly requests them.

5\. Search performance

For the initial version, decrypt and search entries in memory after unlocking. Do not build a persistent plaintext index.

### Acceptance criteria

- Filters can be combined and have documented semantics.
- Search results are deterministic.
- Secret values never appear in ordinary list or search output.
- JSON output is valid and suitable for scripting.
- Search handles malformed entries without silently treating them as valid.

### Out of scope

Full-text search indexes, fuzzy matching, query languages, and searching a locked encrypted vault.

## Phase 3 — Encryption at rest and key management

Deliverable: Secure encrypted vault

### Objective

Replace plaintext persistence with authenticated encryption.

This is the highest-risk phase. Treat cryptographic design and testing as explicit deliverables, not implementation details to improvise.

### Requirements

1\. Unlocking workflow

```
vault add api-key openai
vault search "openai"
vault get openai --field token
```

For commands that access protected data:

1. Read the master password using a hidden prompt.
2. Load the vault's cryptographic metadata.
3. Derive the key with Argon2id.
4. Decrypt and authenticate the relevant entries.
5. Perform the operation.
6. Discard key material and sensitive buffers as far as practical before exiting.

Never accept the master password as a normal command-line argument.

2\. Encrypted file format

The format must represent:

- Format version.
- KDF identifier and parameters.
- Random salt.
- Encryption algorithm identifier.
- Unique nonce per encryption under the same key.
- Ciphertext and authentication tag.

Authenticate critical metadata as associated data, or protect it through an equivalent rigorously defined format. Changing the algorithm identifier or other protected metadata must not allow an attacker to manipulate how data is interpreted without detection.

3\. Key derivation

- Use a maintained Argon2id implementation.
- Use cryptographically random salts.
- Store the KDF parameters needed to derive the key again.
- Set and document resource limits for parsing attacker-controlled metadata.
- Choose parameters based on target-device performance and current security guidance.

4\. Encryption and decryption

- Use a maintained authenticated-encryption implementation.
- Use a cryptographically secure random-number generator.
- Never reuse a nonce with the same key when the chosen algorithm prohibits it.
- Fail closed if authentication fails.
- Never return partial plaintext after an authentication failure.

5\. Password changes

```
vault password change
```

The application must derive the new key and re-encrypt the vault entries safely. It must not merely replace password metadata.

6\. Security-sensitive behavior

- Never log passwords, derived keys, ciphertext plaintext, or secret field values.
- Redact errors that might contain secret data.
- Do not silently fall back to plaintext.
- Keep secret values out of process arguments.
- Do not claim guaranteed memory erasure; implement best-effort zeroization where appropriate.

### Acceptance criteria

- Correct passwords decrypt valid entries.
- Incorrect passwords fail authentication.
- Modified ciphertext or protected metadata is rejected.
- Randomized encryption produces different ciphertext for repeated encryption of the same plaintext.
- Key material is never intentionally written to ordinary vault files.
- Password changes preserve entry contents and invalidate the old password for the re-encrypted data.
- Tests include corruption, malformed crypto metadata, wrong passwords, and known cryptographic test vectors where applicable.

### Out of scope

Persistent unlocked sessions, OS credential-store integration, biometric unlocking, and multi-user access.

## Phase 4 — Safe writes, recovery, and external modification handling

Deliverable: Reliable vault workflow resistant to external file changes

### Objective

Make the encrypted file vault resilient to normal filesystem failures and external changes.

### Requirements

1\. Atomic file updates

- Serialize and validate before replacing an entry.
- Write a temporary file in the same directory.
- Flush as appropriate.
- Atomically replace the destination where supported.
- Report failure if the operation does not complete.
- Document platform-specific durability limitations.

2\. External modifications

If an entry changes outside the application:

- Reload the file when it is next accessed.
- Validate it before use.
- Do not rely on a stale in-memory copy across separate CLI invocations.
- Detect conflicts where practical and report them clearly.

3\. Conflict handling

Do not implement an automatic merge engine.

If external changes create conflicting copies:

- Preserve the original and conflict files.
- Identify suspicious duplicate or conflicting entries.
- Provide a documented manual recovery workflow.
- Never silently pick one conflicting version and discard the other.

4\. Deletion behavior

- Delete only the intended entry.
- Detect duplicate IDs across files.
- Document that synchronized deletions propagate.
- Defer tombstones and distributed deletion reconciliation unless real usage demonstrates a need.

5\. Backup and restore

```
vault backup create
vault backup list
vault restore <backup-id> --dry-run
vault restore <backup-id>
```

- Store backups outside the active vault by default.
- Include the information required to recover encrypted entries.
- Preserve the original files during a restore.
- Validate backups before declaring them restorable.
- Make restore behavior explicit and non-destructive by default.

### Acceptance criteria

- Interrupted writes do not normally leave the active entry partially serialized.
- Corrupt files remain diagnosable and recoverable from backup.
- External changes are not silently overwritten by a stale application process.
- Conflicting copies remain available for manual recovery.
- Backup and restore round-trip the vault successfully.

### Out of scope

Distributed locks, automatic multi-device merges, and a synchronization daemon.

## Phase 5 — Import, export, and portability

Deliverable: Portable vault data

### Objective

Make it easy to move information into and out of the application without confusing plaintext export with encrypted backup.

### Requirements

1\. JSON import/export

```
vault export --format json --output export.json
vault import export.json --dry-run
vault import export.json
```

- Export entries using a documented schema.
- Validate imported data before modifying the vault.
- Detect duplicate IDs and title collisions.
- Offer explicit policies for skip, rename, or replace.
- Support dry-run before bulk imports.

2\. Environment export

```
vault env export my-project --output .env
```

- Export only entries explicitly selected for the operation.
- Require confirmation before overwriting an existing file.
- Warn that `.env` files are plaintext.
- Never export unrelated secrets implicitly.

3\. Encrypted backups

Encrypted backups should preserve the ability to recover the vault without requiring the original directory structure. If a backup uses a separate encryption key or password, document how it is derived and recovered.

4\. Sensitive output

- Warn before plaintext exports.
- Never overwrite an existing export silently.
- Ensure errors do not print secret values.
- Document that deleting an export does not guarantee secure erasure from storage media or backups.

### Acceptance criteria

- Export followed by import preserves supported fields.
- Invalid imports do not partially modify the vault.
- Dry-run reports proposed changes accurately.
- Plaintext exports require an explicit operation.
- Encrypted backups can be restored independently of the active vault.

### Out of scope

Automatic import from every commercial password manager, browser extensions, and cloud integrations.

## Phase 6 — Developer productivity features

Deliverable: Developer-focused secrets toolkit

### Objective

Add features that make this tool worth using beyond basic credential storage.

### Requirements

1\. Secret retrieval

```
vault get openai --field token
vault get home-server --field hostname
```

- Require an explicit retrieval operation for secret values.
- Support a field allowlist or equivalent typed field validation.
- Return nonzero exit codes for missing entries or fields.
- Never print secret values to standard error.
- Document that explicitly retrieved values can still leak through terminal history, logs, or shell pipelines.

2\. Environment management

```
vault env list my-project
vault env export my-project --output .env
```

- Associate environment entries with a project and environment.
- Support development, testing, and production labels.
- Never overwrite existing environment files without explicit approval.
- Ensure exported values are escaped correctly for the target format.

3\. Password generation

```
vault generate password --length 32
```

- Use a cryptographically secure random-number generator.
- Support length and character-set policies.
- Avoid predictable seeds.
- Never store generated passwords automatically unless the user requests it.

4\. Validation and diagnostics

```
vault check --all
vault doctor
```

- Check schema validity, duplicate IDs, unreadable files, and encryption metadata.
- Diagnose configuration and filesystem permission problems.
- Clearly distinguish warnings from errors.
- Never expose decrypted contents in diagnostic output.

5\. Clipboard support

```
vault copy openai --field token
```

- Require explicit selection of the secret field.
- Provide a clear warning that clipboard contents may be accessible to other applications.
- Offer optional clipboard clearing, while acknowledging that clearing is best-effort and clipboard managers may retain copies.

Acceptance criteria

Every feature has automated tests, documented failure behavior, and no unintended disclosure of secret values.

### Out of scope

Automatic credential rotation, API integrations, SSH-agent integration, and browser automation.

## Phase 7 — Release hardening and documentation

Deliverable: Stable MVP release

### Objective

Make the application installable, understandable, and safe enough for real personal use.

### Requirements

- Provide installation instructions and reproducible release builds.
- Document vault initialization, encryption, password changes, backup, restore, and migration.
- Document supported operating systems and filesystems.
- Provide shell completion where practical.
- Add integration tests covering complete user workflows.
- Add dependency auditing and standard Python linting.
- Test recovery from corrupted files and failed imports.
- Test external modifications and conflicting file copies.
- Document threat-model limitations, including malware running under your user account and exposure of explicitly retrieved secrets.

### Acceptance criteria

A user can install the CLI, initialize a vault, create encrypted entries, search and retrieve secrets, synchronize the directory by their chosen means, export selected entries, and restore from a backup using only the documentation.

## Recommended implementation order

### 0

Foundation

Project structure, formats, contracts

### 1

Storage and CRUD

Local files and typed entries

### 2

Search and filters

Daily-use CLI

### 3

Encryption

Master password and authenticated encryption

### 4

Reliability

Atomic writes and conflict recovery

### 5

Import/export

Portability and encrypted backups

### 6

Developer features

Environment exports and utilities

### 7

Release

Documentation and integration testing

One practical adjustment: implement a small encryption proof of concept during Phase 0 to validate the chosen libraries and file format, but don't build the complete vault around plaintext and then retrofit encryption without a migration plan.

## Definition of done for the MVP

The first release is complete when all of these are true:

- Secrets are stored as individual encrypted files.
- The master password is never stored in the vault.
- Search and filtering work after unlocking.
- Secret values are hidden by default.
- CRUD operations preserve stable IDs and validate data.
- Writes are atomic where supported.
- Conflicting file copies are preserved rather than silently merged.
- Import/export and encrypted backup/restore work.
- Corrupted files and incorrect passwords fail safely.
- Automated tests and user documentation cover the core workflows.

My strongest recommendation: treat Phases 0–5 as the core product. Phase 6 makes it especially useful for developers, while Phase 7 makes it dependable. Do not spend time on advanced synchronization, persistent unlock sessions, or a GUI until the encrypted file format and recovery workflow are solid.