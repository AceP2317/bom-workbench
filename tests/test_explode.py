from datetime import date

import pytest

from bom_workbench.errors import CycleError, DepthExceededError, UnknownItemError
from bom_workbench.explode import explode, summarize
from bom_workbench.loaders import load_bom
from bom_workbench.models import BomLine


def test_single_level_quantities(tiny_bom):
    rows = explode(tiny_bom, "A")
    level1 = {(r.item_id, r.extended_qty) for r in rows if r.level == 1}
    assert level1 == {("B", 2.0), ("C", 1.0)}


def test_multilevel_rollup_math(tiny_bom):
    totals = dict((i, q) for i, q, _ in summarize(explode(tiny_bom, "A")))
    # C: 2*3 via B + 1 direct = 7 · D: 7 * 0.5 = 3.5
    assert totals == {"B": 2.0, "C": 7.0, "D": 3.5}


def test_root_qty_scaling(tiny_bom):
    totals = dict((i, q) for i, q, _ in summarize(explode(tiny_bom, "A", qty=10)))
    assert totals == {"B": 20.0, "C": 70.0, "D": 35.0}


def test_leaf_root_returns_empty(tiny_bom):
    assert explode(tiny_bom, "D") == []


def test_unknown_root_raises(tiny_bom):
    with pytest.raises(UnknownItemError):
        explode(tiny_bom, "ZZZ")


def test_cycle_detected(cyclic_bom):
    with pytest.raises(CycleError) as exc:
        explode(cyclic_bom, "A")
    assert exc.value.path == ("A", "B", "A")


def test_self_cycle_detected():
    with pytest.raises(CycleError) as exc:
        explode([BomLine("X", "X", 1.0, "EA")], "X")
    assert exc.value.path == ("X", "X")


def test_max_levels_exceeded(tiny_bom):
    with pytest.raises(DepthExceededError):
        explode(tiny_bom, "A", max_levels=2)


def test_paths_are_full_chains(tiny_bom):
    rows = explode(tiny_bom, "A")
    d_paths = {r.path for r in rows if r.item_id == "D"}
    assert d_paths == {("A", "B", "C", "D"), ("A", "C", "D")}


def test_as_of_selects_validity_window(examples_dir):
    bom = load_bom(examples_dir / "bom.csv")
    before = {r.item_id for r in explode(bom, "FG-AB900", as_of=date(2026, 6, 15))}
    after = {r.item_id for r in explode(bom, "FG-AB900", as_of=date(2026, 7, 15))}
    unfiltered = {r.item_id for r in explode(bom, "FG-AB900")}
    assert "CP-DISP1" in before and "CP-DISP2" not in before
    assert "CP-DISP2" in after and "CP-DISP1" not in after
    assert {"CP-DISP1", "CP-DISP2"} <= unfiltered


def test_demo_gasket_rollup(examples_dir):
    bom = load_bom(examples_dir / "bom.csv")
    totals = dict((i, q) for i, q, _ in summarize(explode(bom, "FG-AB900")))
    # 2 on the brew group + 3 on the boiler + 1 on the portafilter
    assert totals["CP-GASK-S"] == 6.0
    assert totals["RM-STEEL"] == 0.6
    assert totals["CP-SCRM4"] == 12.0  # 8 housing + 4 control panel
