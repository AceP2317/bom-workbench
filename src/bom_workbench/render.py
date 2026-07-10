"""Plain-text tables and CSV output. Stdlib only — no rich, no tabulate."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from .errors import DataError
from .models import ExplosionRow, Item


def fmt_qty(value: float) -> str:
    """Format a quantity without float noise: 6.0 -> '6', 0.6 -> '0.6'."""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Column-aligned text table with a dashed rule under the header."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row: Sequence[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip()

    rule = "  ".join("-" * w for w in widths)
    return "\n".join([fmt(headers), rule, *(fmt(r) for r in rows)])


def render_tree(rows: Sequence[ExplosionRow], items: Mapping[str, Item] | None = None) -> str:
    """Indented explosion tree with extended quantities."""
    lines = []
    for row in rows:
        indent = "  " * (row.level - 1)
        desc = ""
        if items is not None and row.item_id in items:
            desc = f"  {items[row.item_id].description}"
        lines.append(f"{indent}{row.item_id}  x{fmt_qty(row.extended_qty)} {row.uom}{desc}")
    return "\n".join(lines)


def write_csv(path: Path, headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    """Write rows to CSV (utf-8, LF)."""
    try:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(headers)
            writer.writerows(rows)
    except OSError as exc:
        raise DataError(f"cannot write file: {exc}", file=str(path)) from exc
