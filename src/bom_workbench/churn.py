"""Production-plan churn: diff two plan snapshots cell by cell."""

from __future__ import annotations

from collections.abc import Iterable

from .models import ChurnRow, ChurnSummary, PlanRow

ADDED = "ADDED"
DROPPED = "DROPPED"
INCREASED = "INCREASED"
DECREASED = "DECREASED"
UNCHANGED = "UNCHANGED"


def _as_map(rows: Iterable[PlanRow]) -> dict[tuple[str, str], float]:
    totals: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (row.item_id, row.period)
        totals[key] = totals.get(key, 0.0) + row.qty
    return totals


def diff_plans(
    old: Iterable[PlanRow],
    new: Iterable[PlanRow],
    *,
    tolerance: float = 0.0,
) -> tuple[list[ChurnRow], ChurnSummary]:
    """Compare two snapshots keyed by (item_id, period).

    A cell present in both with |delta| <= tolerance is UNCHANGED. A cell
    going to qty 0 is DECREASED (the planner zeroed it); a cell whose row
    disappeared is DROPPED — deliberately different signals. `pct_change`
    is None when the old quantity is 0. Rows come back sorted by key;
    gross churn counts only categorized changes.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")
    old_map = _as_map(old)
    new_map = _as_map(new)

    rows: list[ChurnRow] = []
    counts = {ADDED: 0, DROPPED: 0, INCREASED: 0, DECREASED: 0, UNCHANGED: 0}
    gross = 0.0
    net = 0.0
    for key in sorted(set(old_map) | set(new_map)):
        item_id, period = key
        old_qty = old_map.get(key)
        new_qty = new_map.get(key)
        pct: float | None = None
        if old_qty is None:
            assert new_qty is not None
            category, delta = ADDED, new_qty
        elif new_qty is None:
            category, delta = DROPPED, -old_qty
        else:
            delta = new_qty - old_qty
            # The 1e-9 floor absorbs float noise from summed duplicate rows
            # (0.1 + 0.2 != 0.3) so identical-looking cells never flag.
            if abs(delta) <= max(tolerance, 1e-9):
                category = UNCHANGED
            else:
                category = INCREASED if delta > 0 else DECREASED
            if old_qty != 0:
                pct = delta / old_qty * 100.0
        counts[category] += 1
        net += delta
        if category != UNCHANGED:
            gross += abs(delta)
        rows.append(
            ChurnRow(
                item_id=item_id,
                period=period,
                old_qty=old_qty,
                new_qty=new_qty,
                delta=delta,
                pct_change=pct,
                category=category,
            )
        )

    total_old = sum(old_map.values())
    summary = ChurnSummary(
        added=counts[ADDED],
        dropped=counts[DROPPED],
        increased=counts[INCREASED],
        decreased=counts[DECREASED],
        unchanged=counts[UNCHANGED],
        gross_churn=gross,
        net_delta=net,
        churn_rate=(gross / total_old) if total_old > 0 else None,
        old_rows=len(old_map),
        new_rows=len(new_map),
    )
    return rows, summary
