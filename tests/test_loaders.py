import pytest

from bom_workbench.errors import DataError
from bom_workbench.loaders import load_bom, load_items, load_plan


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_column_named(tmp_path):
    p = write(tmp_path / "bom.csv", "parent_id,child_id,uom\nA,B,EA\n")
    with pytest.raises(DataError, match="qty_per"):
        load_bom(p)


def test_non_numeric_qty_reports_row(tmp_path):
    p = write(
        tmp_path / "bom.csv",
        "parent_id,child_id,qty_per,uom\nA,B,1,EA\nA,C,two,EA\n",
    )
    with pytest.raises(DataError, match="row 3"):
        load_bom(p)


def test_nonpositive_qty_per_rejected(tmp_path):
    p = write(tmp_path / "bom.csv", "parent_id,child_id,qty_per,uom\nA,B,0,EA\n")
    with pytest.raises(DataError, match="> 0"):
        load_bom(p)


def test_blank_validity_dates_load_as_none(tmp_path):
    p = write(
        tmp_path / "bom.csv",
        "parent_id,child_id,qty_per,uom,valid_from,valid_to\nA,B,1,EA,,\n",
    )
    (line,) = load_bom(p)
    assert line.valid_from is None
    assert line.valid_to is None


def test_bad_date_reports_row(tmp_path):
    p = write(
        tmp_path / "bom.csv",
        "parent_id,child_id,qty_per,uom,valid_from,valid_to\nA,B,1,EA,07/01/2026,\n",
    )
    with pytest.raises(DataError, match="ISO date"):
        load_bom(p)


def test_plan_duplicates_summed(tmp_path):
    p = write(
        tmp_path / "plan.csv",
        "item_id,period,qty\nX,2026-W01,10\nX,2026-W01,5\nY,2026-W01,1\n",
    )
    rows = load_plan(p)
    assert [(r.item_id, r.period, r.qty) for r in rows] == [
        ("X", "2026-W01", 15.0),
        ("Y", "2026-W01", 1.0),
    ]


def test_plan_allows_zero_qty(tmp_path):
    p = write(tmp_path / "plan.csv", "item_id,period,qty\nX,2026-W01,0\n")
    (row,) = load_plan(p)
    assert row.qty == 0.0


def test_item_type_validated(tmp_path):
    p = write(
        tmp_path / "items.csv",
        "item_id,description,item_type,base_uom\nA,Widget,made,EA\n",
    )
    with pytest.raises(DataError, match="item_type"):
        load_items(p)


def test_duplicate_item_id_rejected(tmp_path):
    p = write(
        tmp_path / "items.csv",
        "item_id,description,item_type,base_uom\nA,Widget,make,EA\nA,Widget again,buy,EA\n",
    )
    with pytest.raises(DataError, match="duplicate item_id"):
        load_items(p)


def test_row_numbers_are_physical_lines(tmp_path):
    # A blank line before the bad row must not shift the reported number.
    p = write(
        tmp_path / "bom.csv",
        "parent_id,child_id,qty_per,uom\nA,B,1,EA\n\nA,C,two,EA\n",
    )
    with pytest.raises(DataError, match="row 4"):
        load_bom(p)


def test_nan_and_inf_rejected(tmp_path):
    p = write(tmp_path / "plan.csv", "item_id,period,qty\nX,2026-W01,nan\n")
    with pytest.raises(DataError, match="finite"):
        load_plan(p)
    p2 = write(tmp_path / "bom.csv", "parent_id,child_id,qty_per,uom\nA,B,inf,EA\n")
    with pytest.raises(DataError, match="finite"):
        load_bom(p2)


def test_demo_files_load(examples_dir):
    assert len(load_bom(examples_dir / "bom.csv")) == 27
    assert len(load_items(examples_dir / "items.csv")) == 22
    assert len(load_plan(examples_dir / "plan_2026w26.csv")) == 12
