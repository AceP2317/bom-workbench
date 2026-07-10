"""Where-used lookup: walk the BOM upward from a component."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from .models import BomLine, WhereUsedRow


def build_parent_index(bom: Sequence[BomLine]) -> dict[str, list[BomLine]]:
    """Map child_id -> the BOM lines that consume it, preserving input order."""
    index: dict[str, list[BomLine]] = defaultdict(list)
    for line in bom:
        index[line.child_id].append(line)
    return dict(index)


def where_used(
    bom: Sequence[BomLine],
    item: str,
    *,
    max_levels: int | None = None,
    as_of: date | None = None,
) -> list[WhereUsedRow]:
    """Report every usage of `item`, walking up toward top-level parents.

    `max_levels=1` gives direct parents only; `None` walks to the top.
    An ancestor reached via two branches is reported once per path (mirrors
    SAP CS15 multi-level output). On a cyclic BOM the cyclic branch is not
    re-entered, so the walk always terminates — run `bomwb validate` to
    surface cycles themselves. An unused item yields an empty list.
    """
    if max_levels is not None and max_levels < 1:
        return []
    index = build_parent_index(bom)
    rows: list[WhereUsedRow] = []
    initial = [line for line in index.get(item, []) if line.is_valid_on(as_of)]
    # Stack of (line, level, path-so-far); reversed pushes keep input order on pop.
    stack: list[tuple[BomLine, int, tuple[str, ...]]] = [
        (line, 1, (item,)) for line in reversed(initial)
    ]
    while stack:
        line, level, path = stack.pop()
        if line.parent_id in path:
            continue  # cycle — stop this branch
        parent_path = (*path, line.parent_id)
        rows.append(
            WhereUsedRow(
                level=level,
                item_id=line.child_id,
                parent_id=line.parent_id,
                qty_per=line.qty_per,
                path=parent_path,
            )
        )
        if max_levels is not None and level >= max_levels:
            continue
        parents = [ln for ln in index.get(line.parent_id, []) if ln.is_valid_on(as_of)]
        for parent_line in reversed(parents):
            stack.append((parent_line, level + 1, parent_path))
    return rows
