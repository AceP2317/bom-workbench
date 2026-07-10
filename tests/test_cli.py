import csv

from bom_workbench.cli import main


def test_explode_demo(examples_dir, capsys):
    code = main(
        [
            "explode",
            "FG-AB900",
            "--bom",
            str(examples_dir / "bom.csv"),
            "--items",
            str(examples_dir / "items.csv"),
            "--qty",
            "100",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "CP-GASK-S" in out
    assert "Silicone gasket" in out


def test_explode_summary(examples_dir, capsys):
    code = main(["explode", "FG-AB900", "--bom", str(examples_dir / "bom.csv"), "--summary"])
    out = capsys.readouterr().out
    assert code == 0
    assert "total_qty" in out


def test_where_used_demo(examples_dir, capsys):
    code = main(["where-used", "CP-GASK-S", "--bom", str(examples_dir / "bom.csv")])
    out = capsys.readouterr().out
    assert code == 0
    for parent in ("SA-BREW01", "SA-BOILER", "CP-PORTA"):
        assert parent in out


def test_diff_plan_writes_csv(examples_dir, tmp_path, capsys):
    out_csv = tmp_path / "churn.csv"
    code = main(
        [
            "diff-plan",
            str(examples_dir / "plan_2026w26.csv"),
            str(examples_dir / "plan_2026w30.csv"),
            "--csv",
            str(out_csv),
        ]
    )
    assert code == 0
    assert "summary:" in capsys.readouterr().out
    with out_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 8  # 14 cells minus 6 unchanged
    assert {r["category"] for r in rows} == {"ADDED", "DROPPED", "INCREASED", "DECREASED"}


def test_validate_demo_clean(examples_dir, capsys):
    code = main(
        [
            "validate",
            "--bom",
            str(examples_dir / "bom.csv"),
            "--items",
            str(examples_dir / "items.csv"),
        ]
    )
    assert code == 0
    assert "OK" in capsys.readouterr().out


def test_validate_findings_exit_1(tmp_path, capsys):
    bom = tmp_path / "bom.csv"
    bom.write_text(
        "parent_id,child_id,qty_per,uom\nA,B,1,EA\nB,A,1,EA\nA,GHOST,1,EA\n",
        encoding="utf-8",
    )
    items = tmp_path / "items.csv"
    items.write_text(
        "item_id,description,item_type,base_uom\nA,Alpha,make,EA\nB,Beta,buy,EA\n",
        encoding="utf-8",
    )
    code = main(["validate", "--bom", str(bom), "--items", str(items)])
    out = capsys.readouterr().out
    assert code == 1
    assert "cycle:" in out
    assert "GHOST" in out


def test_explode_summary_with_partial_item_master(tmp_path, capsys):
    # A component missing from the master must render blank, not crash.
    bom = tmp_path / "bom.csv"
    bom.write_text("parent_id,child_id,qty_per,uom\nA,B,1,EA\nA,GHOST,2,EA\n", encoding="utf-8")
    items = tmp_path / "items.csv"
    items.write_text(
        "item_id,description,item_type,base_uom\nA,Alpha,make,EA\nB,Beta,buy,EA\n",
        encoding="utf-8",
    )
    code = main(["explode", "A", "--bom", str(bom), "--items", str(items), "--summary"])
    out = capsys.readouterr().out
    assert code == 0
    assert "GHOST" in out


def test_explode_master_only_item_is_leaf(tmp_path, capsys):
    # In the item master but absent from the BOM = a leaf, not an error.
    bom = tmp_path / "bom.csv"
    bom.write_text("parent_id,child_id,qty_per,uom\nA,B,1,EA\n", encoding="utf-8")
    items = tmp_path / "items.csv"
    items.write_text(
        "item_id,description,item_type,base_uom\nA,Alpha,make,EA\nB,Beta,buy,EA\n"
        "LONER,No BOM,buy,EA\n",
        encoding="utf-8",
    )
    code = main(["explode", "LONER", "--bom", str(bom), "--items", str(items)])
    out = capsys.readouterr().out
    assert code == 0
    assert "leaf" in out


def test_validate_effectivity_split_is_not_duplicate(tmp_path, capsys):
    bom = tmp_path / "bom.csv"
    bom.write_text(
        "parent_id,child_id,qty_per,uom,valid_from,valid_to\n"
        "A,B,1,EA,,2026-06-30\n"
        "A,B,2,EA,2026-07-01,\n"  # qty change over time — the normal SAP pattern
        "A,C,1,EA,,\n"
        "A,C,1,EA,,\n",  # true duplicate
        encoding="utf-8",
    )
    code = main(["validate", "--bom", str(bom)])
    out = capsys.readouterr().out
    assert code == 1
    assert "A -> C" in out
    assert "A -> B" not in out


def test_bad_qty_flag_is_clean_exit_1(examples_dir, capsys):
    code = main(["explode", "FG-AB900", "--bom", str(examples_dir / "bom.csv"), "--qty", "0"])
    err = capsys.readouterr().err
    assert code == 1
    assert err.startswith("error:")


def test_data_error_is_clean_exit_1(tmp_path, capsys):
    bom = tmp_path / "bom.csv"
    bom.write_text("parent_id,child_id,qty_per,uom\nA,B,zero,EA\n", encoding="utf-8")
    code = main(["explode", "A", "--bom", str(bom)])
    err = capsys.readouterr().err
    assert code == 1
    assert err.startswith("error:")
    assert "row 2" in err
