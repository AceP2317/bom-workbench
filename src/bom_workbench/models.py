"""Typed records for BOM lines, items, plan rows, and analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Item:
    """One item-master record."""

    item_id: str
    description: str
    item_type: str  # "make" | "buy"
    base_uom: str


@dataclass(frozen=True, slots=True)
class BomLine:
    """One BOM position: `qty_per` of `child_id` goes into one `parent_id`."""

    parent_id: str
    child_id: str
    qty_per: float
    uom: str
    valid_from: date | None = None
    valid_to: date | None = None

    def is_valid_on(self, as_of: date | None) -> bool:
        """True if this line is effective on `as_of` (None = no date filter)."""
        if as_of is None:
            return True
        if self.valid_from is not None and as_of < self.valid_from:
            return False
        return not (self.valid_to is not None and as_of > self.valid_to)


@dataclass(frozen=True, slots=True)
class PlanRow:
    """One production-plan cell: quantity of `item_id` in `period`."""

    item_id: str
    period: str
    qty: float


@dataclass(frozen=True, slots=True)
class ExplosionRow:
    """One line of a multi-level explosion, with the cumulative quantity on its path."""

    level: int
    parent_id: str
    item_id: str
    qty_per: float
    extended_qty: float
    uom: str
    path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WhereUsedRow:
    """One step of a where-used walk: `item_id` is used by `parent_id`."""

    level: int
    item_id: str
    parent_id: str
    qty_per: float
    path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChurnRow:
    """One (item, period) cell compared across two plan snapshots."""

    item_id: str
    period: str
    old_qty: float | None
    new_qty: float | None
    delta: float
    pct_change: float | None
    category: str  # ADDED | DROPPED | INCREASED | DECREASED | UNCHANGED


@dataclass(frozen=True, slots=True)
class ChurnSummary:
    """Aggregate stats for one plan-to-plan comparison."""

    added: int
    dropped: int
    increased: int
    decreased: int
    unchanged: int
    gross_churn: float
    net_delta: float
    churn_rate: float | None
    old_rows: int
    new_rows: int
