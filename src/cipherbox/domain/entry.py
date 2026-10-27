"""Core data model: Entry and its validation/serialization."""

from __future__ import annotations

from dataclasses import dataclass, field, fields as dataclass_fields

from cipherbox.domain.schema import (
    COMMON_FIELDS,
    SCHEMA_VERSION,
    SECRET_TYPES,
)
from cipherbox.errors import InvalidEntryError


@dataclass(frozen=True)
class Entry:
    """A typed secret entry with stable identity and versioned schema."""

    id: str
    schema_version: int
    type: str
    title: str
    tags: list[str]
    created_at: str
    updated_at: str
    fields: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "type": self.type,
            "title": self.title,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "fields": dict(self.fields),
        }


def validate_entry(entry: Entry) -> None:
    """Validate an Entry against the schema contract.

    Raises InvalidEntryError if the type is unknown or any required field
    is missing or empty where required.
    """
    if entry.schema_version != SCHEMA_VERSION:
        raise InvalidEntryError(
            f"unsupported schema version {entry.schema_version}; expected {SCHEMA_VERSION}"
        )
    if entry.type not in SECRET_TYPES:
        raise InvalidEntryError(f"unknown secret type {entry.type!r}")
    if not entry.title:
        raise InvalidEntryError("title is required")


def entry_from_dict(data: dict) -> Entry:
    """Deserialize a dict into an Entry, validating it in the process."""
    if not isinstance(data, dict):
        raise InvalidEntryError("entry data must be a JSON object")
    missing = COMMON_FIELDS - set(data.keys())
    if missing:
        raise InvalidEntryError(f"missing required fields: {sorted(missing)}")
    entry = Entry(
        id=data["id"],
        schema_version=data["schema_version"],
        type=data["type"],
        title=data["title"],
        tags=list(data.get("tags") or []),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        fields=dict(data.get("fields") or {}),
    )
    validate_entry(entry)
    return entry


def entry_to_dict(entry: Entry) -> dict:
    """Serialize an Entry to a plain dict."""
    return entry.to_dict()
