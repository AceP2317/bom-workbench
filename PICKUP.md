# ▶▶ NEXT SESSION — DO FIRST

Live worklist for `bom-workbench`. **Replaced whole at each wrap — never appended to.**

First written 2026-08-08, because the repo had no durable worklist at all (`README.md` was its
only document). That gap is what this file closes — **not** a backlog, because there isn't one.

## State: shipped complete, and genuinely nothing is open

**One commit** (`64c2327`, 2026-07-09), clean tree, in sync with `AceP2317/bom-workbench`, and
**CI green on exactly that commit** — so the last passing run covers the current code, not an
ancestor. 48 tests. Zero runtime dependencies. `bomwb --help` runs.

**There is no open work, and that was established rather than assumed.** Verified 2026-08-08:

- Greps for `TODO`, `FIXME`, `HACK`, `XXX`, `ponytail:`, `NotImplemented`, `not implemented`,
  bare `pass`, `.skip`, `xfail` across every `.py`/`.md`/`.toml`/`.yml` returned **nothing at
  all** — checked with `grep -rn` (which ignores `.ignore` files) and with a canary token
  present in the corpus, so the zero is sighted rather than blind.
- A looser sweep for deferral *language* (`roadmap|backlog|known issue|limitation|next step|
  deferred|future|not yet|for now|later|temporar|first pass|caveat`) returned eight hits, all
  the same false positive: `from __future__ import annotations`, once per module.
- No skipped or xfailed tests. The three matches for `xit` are the substring inside
  `..._exit_1` test names.
- The commit message claims zero dependencies, a typed core, 48 tests and four CLI verbs.
  All four were verified independently.

**So the honest entry is that this repo is finished and untouched since 2026-07-09.** Writing a
backlog here would mean inventing one, which is worse than the gap this file replaces — it would
be `L-007`'s failure one level up: a document that reads like work.

The one real forward signal is a classification, not a task: `pyproject.toml` sets
`Development Status :: 4 - Beta` at version `0.1.0` with no GitHub release cut. That says "not
1.0" without saying what 1.0 would require. **If you want a next step, deciding that is it.**

## What it is

A BOM/MRP toolkit that runs the analyses a production planner actually runs, over plain CSV.
Three of them: multi-level **BOM explosion** with true quantity roll-up along every usage path
plus cycle detection, a depth cap and date-effectivity filtering; **where-used** from any
component up to every top-level parent (SAP CS15-style); and **plan churn**, diffing two
production-plan snapshots into added/dropped/increased/decreased cells.

## Run it

```
pip install -e ".[dev]"     # dev install
bomwb explode | where-used | diff-plan | validate
pytest ; ruff check . ; ruff format --check .
```

Python 3.12+, src-layout, hatchling. Entry point `bomwb = "bom_workbench.cli:main"`; also
`python -m bom_workbench`. **No port** — it is a CLI and a library, and it is registered in
`~/dev/PORTS.md` under "Not web servers", which is the correct entry rather than an omission.

`README.md` is unusually complete for a single document: install, three worked quickstarts with
their real expected output, full input-column tables, a CLI reference with exit-code semantics,
and a library-use snippet. Read it before this file's conventions section — it will answer most
questions.

## Conventions — two of these will bite

- **CI enforces `ruff format --check`, so correct-but-unformatted code FAILS the gate.** Run
  `ruff format .` before pushing. CI order is `ruff check` → `ruff format --check` → `pytest`,
  on Python 3.12 **and** 3.13.
- **Ruff is set to line-length 100, not the 88 default**, with import sorting (`I`) enforced.
  Rules: `E`, `F`, `I`, `UP`, `B`, `SIM`, `RUF`.
- **Zero runtime dependencies is a stated design promise**, not an accident — `dependencies = []`
  and the README's rationale ("`pip install` today works the same in five years"). Importing
  anything outside the standard library at runtime breaks the repo's central claim.
- **The demo data is fictional AND deliberately shaped to exercise edge cases.** The AuroraBrew
  line encodes two finished goods sharing a subassembly, a gasket used on three parents, a KG raw
  material, a validity-dated display swap, and two snapshots with intentional churn.
  `tests/conftest.py` reads from `examples/`, so **regenerating or tidying that data silently
  weakens the suite.**
- **The exit-code contract is public API**: `0` success or clean validate, `1` data error or
  validation findings, `2` usage error. Three CLI tests assert on it.
- **Line endings are pinned and clean** — `.gitattributes` is `* text=auto eol=lf`, and all 27
  tracked files agree with the index. Worth knowing that this repo is the estate's clean
  counterexample: `Ian-PDF-Pro` had no `.gitattributes` at all and a mixed worktree until
  2026-08-08.

## Watch

- **The local `.venv` is Python 3.14.6, while CI covers only 3.12 and 3.13.**
  `tests/__pycache__` carries both `cpython-312` and `cpython-314` artifacts, so it was rebuilt
  onto 3.14 at some point. Not a break in standard-library-only code, but it is the version where
  a failure would go uncaught by the gate. Either add 3.14 to the CI matrix or rebuild the venv
  on a covered version.
- **No `CLAUDE.md`.** If a session ever needs repo-specific instructions beyond what `README.md`
  carries, that is the file to add — but do not add one just to have one.
