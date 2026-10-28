# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is a self-hosted personal project, not an enterprise solution. For this project, simplicity and fast delivery are prioritized over comprehensive feature coverage and maximum completeness.

## Constitution Rules

As per user requirements:
- The agent should not commit itself; it should propose a commit message for changes it made during the session.

## Common Development Commands

Based on the project specification (docs/project-spec.md), this is a Python CLI project. Standard Python commands apply:

- `python -m pip install -e .` - Install the project in editable mode
- `python -m cipherbox` - Run the CLI (equivalent to `vault` command)
- `python -m pytest` - Run all tests
- `ruff check` - Run linting (if ruff is configured)
- `ruff format` - Format code according to ruff

For development workflow:
- To run a specific test: `python -m pytest -k test_name`
- To run tests for a specific module: `python -m pytest tests/<module_name>/`

## Code Architecture and Structure

The project follows a modular Python CLI structure as outlined in the specification (Phase 0):

```
src/cipherbox/
├── cli/          # Command-line interface definition and argument parsing
├── config/       # Application configuration and vault path handling
├── domain/       # Core data models (Entry, Secret types, schemas)
├── storage/      # File system operations for vault entries
├── crypto/       # Cryptographic operations (encryption, decryption, key derivation)
├── services/     # Business logic orchestrating storage, crypto, and domain
├── import_export/# Import/export functionality for vault data
├── backup/       # Backup and restore operations
└── __main__.py   # Application entry point
```

Key architectural principles from the specification:
- CLI-first interface with clear command structure (init, add, list, search, show, get, edit, delete, import, export, backup, restore, check, doctor, generate)
- Local-first design with one JSON file per secret in the vault directory
- Master password derived key kept only in memory during process execution
- Versioned schemas for secret metadata and encrypted file envelopes
- Stable identifiers (UUIDs) for entries independent of filenames
- Deterministic error types and exit codes
- Atomic writes where supported for data safety

The development follows a phased approach:
1. Foundation (project structure, formats, contracts)
2. Storage and CRUD (plaintext prototype)
3. Search and filtering
4. Encryption at rest
5. Safe writes and synchronization compatibility
6. Import/export and portability
7. Developer productivity features
8. Release hardening

Refer to docs/project-spec.md for detailed phase requirements and acceptance criteria.
