"""Multi-level BOM explosion with quantity roll-up."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from .errors import CycleError, DepthExceededError, UnknownItemError
from .models import BomLine, ExplosionRow


def build_child_index(bom: Sequence[BomLine]) -> dict[str, list[BomLine]]:
    """Map parent_id -> its BOM lines, preserving input order."""
    index: dict[str, list[BomLine]] = defaultdict(list)
    for line in bom:
        index[line.parent_id].append(line)
    return dict(index)


def explode(
    bom: Sequence[BomLine],
    root: str,
    *,
    qty: float = 1.0,
    max_levels: int = 25,
    as_of: date | None = None,
) -> list[ExplosionRow]:
    """Explode `root` top-down, multiplying quantities along every path.

    Returns rows in depth-first tree order (level 1 = direct components).
    A component used on several paths appears once per path — `summarize()`
    collapses to per-component totals. Raises CycleError on a cyclic BOM,
    DepthExceededError past `max_levels`, and UnknownItemError when `root`
    appears nowhere in the BOM. `as_of=None` applies no validity filter.
    """
    if qty <= 0:
        raise ValueError("qty must be > 0")
    index = build_child_index(bom)
    if root not in index:
        known = {line.child_id for line in bom}
        if root not in known:
            raise UnknownItemError(root)
        return []  # a real item that is a leaf

    rows: list[ExplosionRow] = []
    # Stack of (line, level, parent_cumulative_qty, parent_path); children are
    # pushed reversed so popping yields depth-first order matching the input.
    stack: list[tuple[BomLine, int, float, tuple[str, ...]]] = [
        (line, 1, qty, (root,))
        for line in reversed([ln for ln in index[root] if ln.is_valid_on(as_of)])
    ]
    while stack:
        line, level, parent_qty, path = stack.pop()
        if line.child_id in path:
            raise CycleError((*path, line.child_id))
        if level > max_levels:
            raise DepthExceededError(max_levels)
        extended = line.qty_per * parent_qty
        child_path = (*path, line.child_id)
        rows.append(
            ExplosionRow(
                level=level,
                parent_id=line.parent_id,
                item_id=line.child_id,
                qty_per=line.qty_per,
                extended_qty=extended,
                uom=line.uom,
                path=child_path,
            )
        )
        children = [ln for ln in index.get(line.child_id, []) if ln.is_valid_on(as_of)]
        for child in reversed(children):
            stack.append((child, level + 1, extended, child_path))
    return rows


def summarize(rows: Sequence[ExplosionRow]) -> list[tuple[str, float, str]]:
    """Collapse explosion rows to (item_id, total_extended_qty, uom), first-seen order."""
    totals: dict[str, float] = {}
    uoms: dict[str, str] = {}
    order: list[str] = []
    for row in rows:
        if row.item_id not in totals:
            totals[row.item_id] = 0.0
            uoms[row.item_id] = row.uom
            order.append(row.item_id)
        totals[row.item_id] += row.extended_qty
    return [(item_id, totals[item_id], uoms[item_id]) for item_id in order]
