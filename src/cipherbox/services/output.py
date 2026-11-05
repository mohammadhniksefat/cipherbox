"""Output formatting: table and redacted JSON for vault entries.

Secret field values are replaced with ``REDACTED`` unless the caller passes
``reveal=True``. Metadata (id, type, title, tags, timestamps) is always shown.
"""

from __future__ import annotations

import json

from cipherbox.domain.entry import Entry

REDACTED = "<redacted>"


def _fields_for(entry: Entry, reveal: bool) -> dict[str, str]:
    if reveal:
        return dict(entry.fields)
    return {key: REDACTED for key in entry.fields}


def format_table(entries: list[Entry], reveal: bool = False) -> str:
    """Render entries as a fixed-width table of metadata with redacted field values."""
    if not entries:
        return "(no entries)"

    headers = ["id", "type", "title", "tags", "updated"]
    rows = []
    for entry in entries:
        rows.append(
            [
                entry.id,
                entry.type,
                entry.title,
                ", ".join(entry.tags) or "(none)",
                entry.updated_at,
            ]
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    lines = []
    lines.append("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(c.ljust(w) for c, w in zip(row, widths)))

    lines.append("")
    for entry in entries:
        fields = _fields_for(entry, reveal)
        lines.append(f"{entry.id} fields:")
        if fields:
            for key in sorted(fields):
                lines.append(f"  {key}: {fields[key]}")
        else:
            lines.append("  (none)")

    return "\n".join(lines)


def format_json(entries: list[Entry], reveal: bool = False) -> str:
    """Render entries as a JSON array of entry dicts with redacted field values."""
    payload = []
    for entry in entries:
        data = entry.to_dict()
        if not reveal:
            data["fields"] = _fields_for(entry, False)
        payload.append(data)
    return json.dumps(payload, indent=2)


def format_list_minimal(entries: list[Entry]) -> str:
    """Render entries as a minimal copy-friendly table of id, type, and title."""
    if not entries:
        return "(no entries)"

    headers = ["id", "type", "title"]
    rows = [[entry.id, entry.type, entry.title] for entry in entries]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    lines = []
    lines.append("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(c.ljust(w) for c, w in zip(row, widths)))

    return "\n".join(lines)


def _field_summary(entry: Entry, reveal: bool) -> list[str]:
    """Per-field lines: length by default, value when revealed."""
    lines: list[str] = []
    for key in sorted(entry.fields):
        value = entry.fields[key]
        if reveal:
            lines.append(f"  {key}: {value}")
        else:
            lines.append(f"  {key}: {len(value)} chars")
    return lines


def format_show_minimal(entry: Entry) -> str:
    """Render a single entry's minimal metadata: id, type, title, tags, field names."""
    lines = [
        f"id:        {entry.id}",
        f"type:      {entry.type}",
        f"title:     {entry.title}",
        f"tags:      {', '.join(entry.tags) or '(none)'}",
    ]
    if entry.fields:
        lines.append("fields:    " + ", ".join(sorted(entry.fields)))
    else:
        lines.append("fields:    (none)")
    return "\n".join(lines)


def format_show_long(entry: Entry, reveal: bool = False) -> str:
    """Render a single entry's long metadata: id, type, title, tags, timestamps,
    and per-field value length (or value when --reveal)."""
    lines = [
        f"id:        {entry.id}",
        f"type:      {entry.type}",
        f"title:     {entry.title}",
        f"tags:      {', '.join(entry.tags) or '(none)'}",
        f"created:   {entry.created_at}",
        f"updated:   {entry.updated_at}",
    ]
    if entry.fields:
        lines.append("fields:")
        lines.extend(_field_summary(entry, reveal))
    else:
        lines.append("fields:    (none)")
    return "\n".join(lines)
