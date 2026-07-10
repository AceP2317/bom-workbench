from bom_workbench.loaders import load_bom
from bom_workbench.where_used import where_used


def test_direct_parents_only(examples_dir):
    bom = load_bom(examples_dir / "bom.csv")
    rows = where_used(bom, "CP-GASK-S", max_levels=1)
    assert {r.parent_id for r in rows} == {"SA-BREW01", "SA-BOILER", "CP-PORTA"}
    assert all(r.level == 1 for r in rows)


def test_multilevel_reaches_both_tops(examples_dir):
    bom = load_bom(examples_dir / "bom.csv")
    rows = where_used(bom, "CP-PCB01")
    assert {r.parent_id for r in rows if r.level == 1} == {"SA-UI01"}
    assert {r.parent_id for r in rows if r.level == 2} == {"FG-AB900", "FG-AB600"}


def test_unused_item_yields_empty(tiny_bom):
    assert where_used(tiny_bom, "A") == []


def test_multilevel_paths(tiny_bom):
    rows = where_used(tiny_bom, "D")
    paths = {r.path for r in rows}
    assert ("D", "C", "B", "A") in paths
    assert ("D", "C", "A") in paths


def test_cycle_safe_terminates(cyclic_bom):
    rows = where_used(cyclic_bom, "A")
    assert [r.parent_id for r in rows] == ["B"]


def test_levels_zero_or_negative_yields_empty(tiny_bom):
    assert where_used(tiny_bom, "D", max_levels=0) == []
    assert where_used(tiny_bom, "D", max_levels=-1) == []
