# bom-workbench

[![CI](https://github.com/AceP2317/bom-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/AceP2317/bom-workbench/actions/workflows/ci.yml)

BOM/MRP data toolkit over plain CSV — the analyses a planner actually runs,
as a small typed Python package with a CLI.

- **BOM explosion** — multi-level, with true quantity roll-up along every
  usage path, cycle detection, a depth cap, and date-effectivity filtering.
- **Where-used** — from any component up to every top-level parent
  (SAP CS15-style), or direct parents only.
- **Plan churn** — diff two production-plan snapshots into
  added / dropped / increased / decreased cells with summary stats, and the
  distinction that matters: a line **zeroed** by a planner is a decrease,
  a line that **disappeared** is a drop.

## Why zero dependencies

Everything runs on the Python standard library (`csv`, `argparse`,
`dataclasses`). Nothing to pin, nothing to rot — `pip install` today works
the same in five years. Dev tooling (pytest, ruff) is an optional extra.

## Install

Python 3.12+.

```
git clone https://github.com/AceP2317/bom-workbench
cd bom-workbench
pip install .
```

## Quickstart

The `examples/` folder ships a fictional espresso-machine product line
(see [Demo data](#demo-data)). Three commands to try:

**Explode a finished good** (build 100 units — what do I need?):

```
bomwb explode FG-AB900 --bom examples/bom.csv --items examples/items.csv --qty 100 --summary
```

```text
FG-AB900 x100 - 22 line(s)
component  total_qty  uom  description
---------  ---------  ---  ----------------------
SA-BREW01  100        EA   Brew group assembly
CP-PUMP15  100        EA   15-bar vibration pump
SA-BOILER  100        EA   Boiler assembly
CP-HEAT12  100        EA   Heating element 1200 W
CP-THERM   200        EA   Thermostat
CP-GASK-S  600        EA   Silicone gasket
RM-STEEL   60         KG   Stainless steel sheet
CP-VALV3   100        EA   3-way solenoid valve
SA-HOUS01  100        EA   Housing assembly
CP-PANL-L  200        EA   Side panel
RM-ABS     80         KG   ABS resin
CP-SCRM4   1200       EA   M4 screw
SA-UI01    100        EA   Control panel assembly
CP-PCB01   100        EA   Controller PCB
CP-DISP1   100        EA   OLED display
CP-DISP2   100        EA   LCD display
CP-PORTA   100        EA   Portafilter
CP-CORD    100        EA   Power cord
CP-MANL    100        EA   User manual
```

(Both displays show because no date filter was applied — add
`--as-of 2026-07-15` and only the LCD display survives the validity window.)

**Where is this component used?**

```
bomwb where-used CP-GASK-S --bom examples/bom.csv
```

```text
where-used: CP-GASK-S - 7 usage(s)
level  used_by    qty_per  path
-----  ---------  -------  --------------------------------------------
1      SA-BREW01  2        CP-GASK-S > SA-BREW01
2      FG-AB900   1        CP-GASK-S > SA-BREW01 > FG-AB900
1      SA-BOILER  3        CP-GASK-S > SA-BOILER
2      SA-BREW01  1        CP-GASK-S > SA-BOILER > SA-BREW01
3      FG-AB900   1        CP-GASK-S > SA-BOILER > SA-BREW01 > FG-AB900
1      CP-PORTA   1        CP-GASK-S > CP-PORTA
2      FG-AB900   1        CP-GASK-S > CP-PORTA > FG-AB900
```

**What changed between two plan versions?**

```
bomwb diff-plan examples/plan_2026w26.csv examples/plan_2026w30.csv
```

```text
plan churn: examples/plan_2026w26.csv -> examples/plan_2026w30.csv
item      period    old  new  delta  pct      category
--------  --------  ---  ---  -----  -------  ---------
FG-AB900  2026-W32  -    550  550    -        ADDED
FG-AB900  2026-W33  -    550  550    -        ADDED
FG-AB600  2026-W30  300  -    -300   -        DROPPED
FG-AB600  2026-W31  300  -    -300   -        DROPPED
FG-AB600  2026-W28  250  0    -250   -100.0%  DECREASED
FG-AB900  2026-W28  400  480  80     +20.0%   INCREASED
FG-AB900  2026-W29  450  520  70     +15.6%   INCREASED
FG-AB900  2026-W30  450  510  60     +13.3%   INCREASED

summary: added 2 | dropped 2 | increased 3 | decreased 1 | unchanged 6
gross churn 2160 | net delta 460 | churn rate 59.5% | cells 12 -> 12
```

## Input formats

**BOM lines** (`--bom`): one row per BOM position.

| column | type | notes |
|---|---|---|
| `parent_id` | text | required |
| `child_id` | text | required |
| `qty_per` | number > 0 | quantity of child per 1 parent |
| `uom` | text | `EA`, `KG`, … |
| `valid_from` | ISO date or blank | optional column; blank = always valid |
| `valid_to` | ISO date or blank | optional column; blank = open-ended |

**Item master** (`--items`, optional): enriches output and enables
referential checks in `validate`.

| column | type | notes |
|---|---|---|
| `item_id` | text | unique |
| `description` | text | |
| `item_type` | `make` \| `buy` | |
| `base_uom` | text | |

**Plan snapshot** (`diff-plan` inputs): one row per item/period cell.
Duplicate `(item_id, period)` rows are summed on load. `period` is an
opaque key — ISO weeks, dates, months all work.

| column | type |
|---|---|
| `item_id` | text |
| `period` | text |
| `qty` | number ≥ 0 |

## CLI reference

| command | what it does | key flags |
|---|---|---|
| `bomwb explode ITEM` | multi-level explosion (tree, or `--summary` totals) | `--bom` `--items` `--qty` `--max-levels` `--as-of` `--csv` |
| `bomwb where-used ITEM` | every usage, walking up to top level | `--bom` `--levels` `--as-of` `--csv` |
| `bomwb diff-plan OLD NEW` | churn table + summary between two snapshots | `--tolerance` `--include-unchanged` `--csv` |
| `bomwb validate` | cycles, item-master orphans, duplicate lines | `--bom` `--items` |

Exit codes: `0` success / clean validate, `1` data error or validation
findings, `2` usage error. `--csv OUT.csv` writes the displayed rows for
spreadsheet work (for `diff-plan`, add `--include-unchanged` to capture
every cell); `--as-of YYYY-MM-DD` applies BOM date effectivity.

## Library use

```python
from bom_workbench import load_bom, explode, summarize

bom = load_bom("examples/bom.csv")
rows = explode(bom, "FG-AB900", qty=100)
for item_id, total, uom in summarize(rows):
    print(item_id, total, uom)
```

## Demo data

All data in `examples/` is fictional — the **AuroraBrew** product line does
not exist. It is shaped to exercise the interesting cases: two finished
goods sharing a subassembly, a gasket used on three different parents, a
raw material in KG, a display swap with validity dates, and two plan
snapshots with deliberate churn.

## Development

```
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

## License

[MIT](LICENSE)
