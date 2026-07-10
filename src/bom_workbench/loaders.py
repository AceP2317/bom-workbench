"""CSV loaders. Every validation failure raises DataError with file + row context.

Row numbers in errors are physical file lines (header = line 1), matching
what a spreadsheet shows even when the file contains blank lines.
"""

from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

from .errors import DataError
from .models import BomLine, Item, PlanRow

BOM_COLUMNS = ("parent_id", "child_id", "qty_per", "uom")
ITEM_COLUMNS = ("item_id", "description", "item_type", "base_uom")
PLAN_COLUMNS = ("item_id", "period", "qty")

ITEM_TYPES = ("make", "buy")


def _read_rows(path: Path, required: tuple[str, ...]) -> list[tuple[int, dict[str, str]]]:
    """Return (physical_line_number, row) pairs; validates the header."""
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            headers = reader.fieldnames or []
            missing = [c for c in required if c not in headers]
            if missing:
                raise DataError(f"missing required column(s): {', '.join(missing)}", file=str(path))
            return [(reader.line_num, row) for row in reader]
    except (OSError, UnicodeDecodeError) as exc:
        raise DataError(f"cannot read file: {exc}", file=str(path)) from exc


def _require(value: str | None, column: str, path: Path, row: int) -> str:
    value = (value or "").strip()
    if not value:
        raise DataError(f"{column} is empty", file=str(path), row=row)
    return value


def _parse_qty(raw: str | None, column: str, path: Path, row: int, *, allow_zero: bool) -> float:
    text = (raw or "").strip()
    try:
        value = float(text)
    except ValueError as exc:
        raise DataError(f"{column} is not a number: {text!r}", file=str(path), row=row) from exc
    if not math.isfinite(value):
        raise DataError(f"{column} is not a finite number: {text!r}", file=str(path), row=row)
    if value < 0 or (value == 0 and not allow_zero):
        bound = ">= 0" if allow_zero else "> 0"
        raise DataError(f"{column} must be {bound}: {text!r}", file=str(path), row=row)
    return value


def _parse_date(raw: str | None, column: str, path: Path, row: int) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise DataError(
            f"{column} is not an ISO date (YYYY-MM-DD): {text!r}", file=str(path), row=row
        ) from exc


def load_bom(path: str | Path) -> list[BomLine]:
    """Load BOM lines from CSV: parent_id, child_id, qty_per, uom[, valid_from, valid_to]."""
    path = Path(path)
    lines: list[BomLine] = []
    for row_no, row in _read_rows(path, BOM_COLUMNS):
        valid_from = _parse_date(row.get("valid_from"), "valid_from", path, row_no)
        valid_to = _parse_date(row.get("valid_to"), "valid_to", path, row_no)
        if valid_from is not None and valid_to is not None and valid_from > valid_to:
            raise DataError("valid_from is after valid_to", file=str(path), row=row_no)
        lines.append(
            BomLine(
                parent_id=_require(row.get("parent_id"), "parent_id", path, row_no),
                child_id=_require(row.get("child_id"), "child_id", path, row_no),
                qty_per=_parse_qty(row.get("qty_per"), "qty_per", path, row_no, allow_zero=False),
                uom=_require(row.get("uom"), "uom", path, row_no),
                valid_from=valid_from,
                valid_to=valid_to,
            )
        )
    return lines


def load_items(path: str | Path) -> dict[str, Item]:
    """Load the item master from CSV (columns: item_id, description, item_type, base_uom)."""
    path = Path(path)
    items: dict[str, Item] = {}
    for row_no, row in _read_rows(path, ITEM_COLUMNS):
        item_id = _require(row.get("item_id"), "item_id", path, row_no)
        if item_id in items:
            raise DataError(f"duplicate item_id: {item_id}", file=str(path), row=row_no)
        item_type = _require(row.get("item_type"), "item_type", path, row_no).lower()
        if item_type not in ITEM_TYPES:
            raise DataError(
                f"item_type must be one of {ITEM_TYPES}: {item_type!r}", file=str(path), row=row_no
            )
        items[item_id] = Item(
            item_id=item_id,
            description=(row.get("description") or "").strip(),
            item_type=item_type,
            base_uom=_require(row.get("base_uom"), "base_uom", path, row_no),
        )
    return items


def load_plan(path: str | Path) -> list[PlanRow]:
    """Load a plan snapshot from CSV (columns: item_id, period, qty).

    Duplicate (item_id, period) rows are summed — snapshots exported from
    planning systems often carry one row per order rather than per cell.
    """
    path = Path(path)
    totals: dict[tuple[str, str], float] = {}
    order: list[tuple[str, str]] = []
    for row_no, row in _read_rows(path, PLAN_COLUMNS):
        key = (
            _require(row.get("item_id"), "item_id", path, row_no),
            _require(row.get("period"), "period", path, row_no),
        )
        qty = _parse_qty(row.get("qty"), "qty", path, row_no, allow_zero=True)
        if key not in totals:
            totals[key] = 0.0
            order.append(key)
        totals[key] += qty
    return [
        PlanRow(item_id=item, period=period, qty=totals[(item, period)]) for item, period in order
    ]
