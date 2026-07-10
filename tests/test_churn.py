import pytest

from bom_workbench.churn import diff_plans
from bom_workbench.loaders import load_plan
from bom_workbench.models import PlanRow


def plan(*cells):
    return [PlanRow(item_id=i, period=p, qty=q) for i, p, q in cells]


def test_all_categories_classified():
    old = plan(("A", "W1", 100), ("B", "W1", 50), ("C", "W1", 30), ("D", "W1", 10))
    new = plan(("A", "W1", 100), ("B", "W1", 80), ("C", "W1", 5), ("E", "W1", 40))
    rows, _ = diff_plans(old, new)
    by_key = {(r.item_id): r.category for r in rows}
    assert by_key == {
        "A": "UNCHANGED",
        "B": "INCREASED",
        "C": "DECREASED",
        "D": "DROPPED",
        "E": "ADDED",
    }


def test_zeroed_is_decreased_not_dropped():
    rows, _ = diff_plans(plan(("A", "W1", 500)), plan(("A", "W1", 0)))
    (row,) = rows
    assert row.category == "DECREASED"
    assert row.delta == -500


def test_pct_change_none_when_old_zero():
    rows, _ = diff_plans(plan(("A", "W1", 0)), plan(("A", "W1", 25)))
    (row,) = rows
    assert row.category == "INCREASED"
    assert row.pct_change is None


def test_tolerance_suppresses_noise():
    rows, summary = diff_plans(plan(("A", "W1", 100.0)), plan(("A", "W1", 100.4)), tolerance=0.5)
    assert rows[0].category == "UNCHANGED"
    assert summary.gross_churn == 0.0


def test_summary_math():
    old = plan(("A", "W1", 100), ("B", "W1", 50))
    new = plan(("A", "W1", 130), ("C", "W1", 20))
    _, s = diff_plans(old, new)
    assert (s.added, s.dropped, s.increased, s.decreased, s.unchanged) == (1, 1, 1, 0, 0)
    assert s.gross_churn == 30 + 50 + 20
    assert s.net_delta == 30 - 50 + 20
    assert s.churn_rate == pytest.approx(100 / 150)
    assert (s.old_rows, s.new_rows) == (2, 2)


def test_float_noise_from_summed_duplicates_is_unchanged():
    # 0.1 + 0.2 != 0.3 in floats; the built-in noise floor absorbs it.
    old = plan(("A", "W1", 0.1), ("A", "W1", 0.2))
    new = plan(("A", "W1", 0.3))
    rows, s = diff_plans(old, new)
    assert rows[0].category == "UNCHANGED"
    assert s.gross_churn == 0.0


def test_empty_old_snapshot_all_added():
    rows, s = diff_plans([], plan(("A", "W1", 10)))
    assert rows[0].category == "ADDED"
    assert s.churn_rate is None


def test_demo_snapshots(examples_dir):
    old = load_plan(examples_dir / "plan_2026w26.csv")
    new = load_plan(examples_dir / "plan_2026w30.csv")
    rows, s = diff_plans(old, new)
    assert (s.added, s.dropped, s.increased, s.decreased, s.unchanged) == (2, 2, 3, 1, 6)
    assert s.gross_churn == 2160.0
    assert s.net_delta == 460.0
    assert len(rows) == 14
