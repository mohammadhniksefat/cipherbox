"""Import/export for the cipherbox vault.

Export serializes the vault to a documented JSON schema
(``cipherbox-export/1``). Import validates every entry *before* writing
anything, so an invalid import never partially modifies the vault.
Duplicate IDs within the import file and against the active vault are
detected; an explicit policy (skip / replace / rename) decides what to do
about collisions. Dry-run reports proposed changes without writing.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from cipherbox.domain.entry import Entry, entry_from_dict
from cipherbox.errors import EXIT_ERROR, VaultError
from cipherbox.storage.repository import VaultRepository

EXPORT_FORMAT = "cipherbox-export/1"


class ExportError(VaultError):
    """Raised when exporting the vault fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_ERROR)


class ImportError(VaultError):
    """Raised when importing fails validation or cannot be completed.

    Fail closed: nothing is written to the vault when this is raised.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_ERROR)


@dataclass(frozen=True)
class ImportPolicy:
    """How to handle an entry whose id already exists in the vault."""

    mode: str  # "skip", "replace", or "rename"

    def __post_init__(self) -> None:
        if self.mode not in {"skip", "replace", "rename"}:
            raise ValueError(
                f"invalid import policy {self.mode!r}; expected 'skip', 'replace', or 'rename'"
            )


@dataclass(frozen=True)
class ImportReport:
    """The result of an import operation."""

    imported: list[str]
    skipped: list[str]
    replaced: list[str]
    renamed: list[tuple[str, str]]
    warnings: list[str]
    dry_run: bool


def export_entries(
    repo: VaultRepository,
    output: str | Path,
    *,
    format: str = EXPORT_FORMAT,
    overwrite: bool = False,
) -> str:
    """Serialize the vault to a ``cipherbox-export/1`` JSON document.

    Writes ``format``, ``exported_at``, ``source_vault``, and ``entries``
    (each an ``Entry.to_dict()``) to ``output``. Refuses to overwrite an
    existing file unless ``overwrite`` is True. Returns the output path.
    """
    output = Path(output)
    if output.exists() and not overwrite:
        raise FileExistsError(
            f"output file {output} already exists; pass --confirm to overwrite"
        )

    entries = repo.list()
    from datetime import UTC, datetime

    payload = {
        "format": format,
        "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_vault": str(repo.vault_path),
        "entries": [entry.to_dict() for entry in entries],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(output)


def import_entries(
    repo: VaultRepository,
    input: str | Path,
    *,
    policy: ImportPolicy,
    dry_run: bool = False,
) -> ImportReport:
    """Import entries from a ``cipherbox-export/1`` JSON document.

    Every entry is validated with :func:`entry_from_dict` before anything
    is written, so an invalid file raises :class:`ImportError` and the
    vault is left unchanged. Duplicate ids within the file itself are
    rejected. Collisions against the active vault are resolved by
    ``policy`` (skip / replace / rename). Title collisions against the
    vault are reported in ``warnings`` but do not block import.

    ``dry_run=True`` reports what would be done without writing anything.
    """
    input = Path(input)
    try:
        data = json.loads(input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ImportError(f"cannot read import file {input}: {exc}") from exc

    if not isinstance(data, dict) or "entries" not in data:
        raise ImportError(f"import file {input} is not a cipherbox export document")
    raw_entries = data["entries"]
    if not isinstance(raw_entries, list):
        raise ImportError(f"import file {input} has a non-list 'entries' field")

    # Validate every entry before writing anything (fail closed).
    parsed: list[Entry] = []
    seen_ids: set[str] = set()
    for raw in raw_entries:
        try:
            entry = entry_from_dict(raw)
        except VaultError as exc:
            raise ImportError(f"invalid entry in import file {input}: {exc}") from exc
        if entry.id in seen_ids:
            raise ImportError(
                f"duplicate entry id {entry.id!r} within import file {input}"
            )
        seen_ids.add(entry.id)
        parsed.append(entry)

    existing = {entry.id: entry for entry in repo.list()}
    existing_titles = {entry.title for entry in repo.list()}

    imported: list[str] = []
    skipped: list[str] = []
    replaced: list[str] = []
    renamed: list[tuple[str, str]] = []
    warnings: list[str] = []

    for entry in parsed:
        # Title collision warning (does not block import).
        if entry.title in existing_titles:
            warnings.append(
                f"title {entry.title!r} already exists in the vault (entry {entry.id})"
            )

        if entry.id in existing:
            if policy.mode == "skip":
                skipped.append(entry.id)
                continue
            if policy.mode == "replace":
                if not dry_run:
                    repo.edit(entry.id, entry.to_dict())
                replaced.append(entry.id)
                continue
            if policy.mode == "rename":
                new_id = str(uuid.uuid4())
                renamed_entry = Entry(
                    id=new_id,
                    schema_version=entry.schema_version,
                    type=entry.type,
                    title=entry.title,
                    tags=list(entry.tags),
                    created_at=entry.created_at,
                    updated_at=entry.updated_at,
                    fields=dict(entry.fields),
                )
                if not dry_run:
                    repo.add(renamed_entry)
                renamed.append((entry.id, new_id))
                continue
        else:
            if not dry_run:
                repo.add(entry)
            imported.append(entry.id)

    return ImportReport(
        imported=imported,
        skipped=skipped,
        replaced=replaced,
        renamed=renamed,
        warnings=warnings,
        dry_run=dry_run,
    )
