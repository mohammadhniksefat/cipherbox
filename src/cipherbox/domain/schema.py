"""Versioned schema for secret entries."""

from __future__ import annotations

SCHEMA_VERSION = 1

SECRET_TYPES = frozenset(
    {"login", "api-key", "ssh", "secure-note", "env", "recovery"}
)

# Common metadata fields every entry carries, in addition to type-specific fields.
COMMON_FIELDS = frozenset(
    {
        "id",
        "schema_version",
        "type",
        "title",
        "tags",
        "created_at",
        "updated_at",
        "fields",
    }
)
