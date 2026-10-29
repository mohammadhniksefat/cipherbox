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
