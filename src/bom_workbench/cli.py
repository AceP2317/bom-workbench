"""The `bomwb` command-line interface.

Exit codes: 0 success (or clean validate), 1 data error / validation
findings, 2 usage error (argparse).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .churn import UNCHANGED, diff_plans
from .errors import BomWorkbenchError, UnknownItemError
from .explode import build_child_index, explode, summarize
from .loaders import load_bom, load_items, load_plan
from .models import BomLine, Item
from .render import fmt_qty, render_table, render_tree, write_csv
from .where_used import where_used


def _fmt_opt(value: float | None) -> str:
    return "-" if value is None else fmt_qty(value)


def cmd_explode(args: argparse.Namespace) -> int:
    bom = load_bom(args.bom)
    items = load_items(args.items) if args.items else None
    if items is not None and args.item not in items:
        raise UnknownItemError(args.item)
    try:
        rows = explode(bom, args.item, qty=args.qty, max_levels=args.max_levels, as_of=args.as_of)
    except UnknownItemError:
        if items is None or args.item not in items:
            raise
        rows = []  # confirmed by the item master, just carries no BOM — a leaf
    print(f"{args.item} x{fmt_qty(args.qty)} - {len(rows)} line(s)")
    if not rows:
        print("(no components - leaf item)")
        return 0
    if args.summary:
        table = [
            (
                item_id,
                fmt_qty(total),
                uom,
                items[item_id].description if items and item_id in items else "",
            )
            for item_id, total, uom in summarize(rows)
        ]
        headers = ("component", "total_qty", "uom") + (("description",) if items else ())
        print(render_table(headers, [r[: len(headers)] for r in table]))
    else:
        print(render_tree(rows, items))
    if args.csv:
        write_csv(
            args.csv,
            ("level", "parent_id", "item_id", "qty_per", "extended_qty", "uom", "path"),
            [
                (
                    r.level,
                    r.parent_id,
                    r.item_id,
                    r.qty_per,
                    r.extended_qty,
                    r.uom,
                    " > ".join(r.path),
                )
                for r in rows
            ],
        )
        print(f"wrote {args.csv}")
    return 0


def cmd_where_used(args: argparse.Namespace) -> int:
    bom = load_bom(args.bom)
    rows = where_used(bom, args.item, max_levels=args.levels, as_of=args.as_of)
    print(f"where-used: {args.item} - {len(rows)} usage(s)")
    if not rows:
        print("(not used in any BOM)")
        return 0
    table = [
        (
            str(r.level),
            r.parent_id,
            fmt_qty(r.qty_per),
            " > ".join(r.path),
        )
        for r in rows
    ]
    print(render_table(("level", "used_by", "qty_per", "path"), table))
    if args.csv:
        write_csv(
            args.csv,
            ("level", "item_id", "parent_id", "qty_per", "path"),
            [(r.level, r.item_id, r.parent_id, r.qty_per, " > ".join(r.path)) for r in rows],
        )
        print(f"wrote {args.csv}")
    return 0


def cmd_diff_plan(args: argparse.Namespace) -> int:
    old = load_plan(args.old)
    new = load_plan(args.new)
    rows, s = diff_plans(old, new, tolerance=args.tolerance)
    shown = [r for r in rows if args.include_unchanged or r.category != UNCHANGED]
    shown.sort(key=lambda r: abs(r.delta), reverse=True)
    print(f"plan churn: {args.old} -> {args.new}")
    if shown:
        table = [
            (
                r.item_id,
                r.period,
                _fmt_opt(r.old_qty),
                _fmt_opt(r.new_qty),
                fmt_qty(r.delta),
                "-" if r.pct_change is None else f"{r.pct_change:+.1f}%",
                r.category,
            )
            for r in shown
        ]
        print(render_table(("item", "period", "old", "new", "delta", "pct", "category"), table))
    else:
        print("(no changes)")
    print()
    rate = "-" if s.churn_rate is None else f"{s.churn_rate * 100:.1f}%"
    print(
        f"summary: added {s.added} | dropped {s.dropped} | increased {s.increased}"
        f" | decreased {s.decreased} | unchanged {s.unchanged}"
    )
    print(
        f"gross churn {fmt_qty(s.gross_churn)} | net delta {fmt_qty(s.net_delta)}"
        f" | churn rate {rate} | cells {s.old_rows} -> {s.new_rows}"
    )
    if args.csv:
        write_csv(
            args.csv,
            ("item_id", "period", "old_qty", "new_qty", "delta", "pct_change", "category"),
            [
                (
                    r.item_id,
                    r.period,
                    "" if r.old_qty is None else r.old_qty,
                    "" if r.new_qty is None else r.new_qty,
                    r.delta,
                    "" if r.pct_change is None else round(r.pct_change, 2),
                    r.category,
                )
                for r in shown
            ],
        )
        print(f"wrote {args.csv}")
    return 0


def _find_cycles(bom: Sequence[BomLine]) -> list[tuple[str, ...]]:
    """Full-graph cycle scan (iterative colored DFS); returns each cycle once."""
    index = build_child_index(bom)
    white, gray, black = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(
        {line.parent_id for line in bom} | {line.child_id for line in bom}, white
    )
    cycles: list[tuple[str, ...]] = []
    for start in sorted(color):
        if color[start] != white:
            continue
        color[start] = gray
        path = [start]
        stack = [(start, iter(index.get(start, [])))]
        while stack:
            node, children = stack[-1]
            advanced = False
            for line in children:
                child = line.child_id
                if color[child] == gray:
                    at = path.index(child)
                    cycles.append((*path[at:], child))
                elif color[child] == white:
                    color[child] = gray
                    path.append(child)
                    stack.append((child, iter(index.get(child, []))))
                    advanced = True
                    break
            if not advanced:
                color[node] = black
                path.pop()
                stack.pop()
    return cycles


def cmd_validate(args: argparse.Namespace) -> int:
    bom = load_bom(args.bom)
    items: dict[str, Item] | None = load_items(args.items) if args.items else None
    findings: list[str] = []

    for cycle in _find_cycles(bom):
        findings.append("cycle: " + " -> ".join(cycle))

    if items is not None:
        referenced: dict[str, str] = {}
        for line in bom:
            referenced.setdefault(line.parent_id, "parent")
            referenced.setdefault(line.child_id, "child")
        for item_id in sorted(referenced):
            if item_id not in items:
                findings.append(
                    f"BOM references item missing from item master: {item_id}"
                    f" (as {referenced[item_id]})"
                )

    # Same parent/child with different validity windows is the normal
    # date-effectivity pattern, not a duplicate — key on the full identity.
    seen: dict[tuple[str, str, date | None, date | None], int] = {}
    for line in bom:
        key = (line.parent_id, line.child_id, line.valid_from, line.valid_to)
        seen[key] = seen.get(key, 0) + 1
    flagged: dict[tuple[str, str], int] = {}
    for (parent_id, child_id, _, _), count in seen.items():
        if count > 1:
            flagged[(parent_id, child_id)] = flagged.get((parent_id, child_id), 0) + count
    for (parent_id, child_id), count in sorted(flagged.items()):
        findings.append(f"duplicate BOM line: {parent_id} -> {child_id} ({count} lines)")

    if findings:
        for finding in findings:
            print(f"FINDING: {finding}")
        print(f"validate: {len(findings)} finding(s)")
        return 1
    checked = f"{len(bom)} BOM line(s)" + (f", {len(items)} item(s)" if items else "")
    print(f"validate: OK - {checked}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="bomwb", description="BOM/MRP data toolkit over plain CSV."
    )
    parser.add_argument("--version", action="version", version=f"bomwb {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("explode", help="Multi-level BOM explosion with quantity roll-up.")
    p.add_argument("item", help="Item to explode (e.g. a finished good).")
    p.add_argument("--bom", required=True, type=Path, help="BOM lines CSV.")
    p.add_argument("--items", type=Path, help="Item master CSV (adds descriptions).")
    p.add_argument("--qty", type=float, default=1.0, help="Root quantity (default 1).")
    p.add_argument("--max-levels", type=int, default=25, help="Depth cap (default 25).")
    p.add_argument(
        "--as-of",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Only BOM lines valid on this date.",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        help="Collapse to per-component totals instead of the tree.",
    )
    p.add_argument("--csv", type=Path, metavar="OUT.csv", help="Also write rows to CSV.")
    p.set_defaults(func=cmd_explode)

    p = sub.add_parser("where-used", help="Find every BOM that consumes an item.")
    p.add_argument("item", help="Component to look up.")
    p.add_argument("--bom", required=True, type=Path, help="BOM lines CSV.")
    p.add_argument(
        "--levels",
        type=int,
        default=None,
        metavar="N",
        help="Walk at most N levels up (default: to the top).",
    )
    p.add_argument(
        "--as-of",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Only BOM lines valid on this date.",
    )
    p.add_argument("--csv", type=Path, metavar="OUT.csv", help="Also write rows to CSV.")
    p.set_defaults(func=cmd_where_used)

    p = sub.add_parser("diff-plan", help="Churn analysis between two plan snapshots.")
    p.add_argument("old", help="Older snapshot CSV.")
    p.add_argument("new", help="Newer snapshot CSV.")
    p.add_argument(
        "--tolerance",
        type=float,
        default=0.0,
        help="Treat |delta| <= this as unchanged (default 0).",
    )
    p.add_argument("--include-unchanged", action="store_true", help="Show unchanged cells too.")
    p.add_argument("--csv", type=Path, metavar="OUT.csv", help="Also write rows to CSV.")
    p.set_defaults(func=cmd_diff_plan)

    p = sub.add_parser("validate", help="Integrity checks: cycles, orphans, duplicates.")
    p.add_argument("--bom", required=True, type=Path, help="BOM lines CSV.")
    p.add_argument("--items", type=Path, help="Item master CSV (enables orphan checks).")
    p.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (BomWorkbenchError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
