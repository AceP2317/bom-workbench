from pathlib import Path

import pytest

from bom_workbench.models import BomLine

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def tiny_bom() -> list[BomLine]:
    """A: B x2, C x1 · B: C x3 · C: D x0.5 — shared C, three levels deep."""
    return [
        BomLine("A", "B", 2.0, "EA"),
        BomLine("A", "C", 1.0, "EA"),
        BomLine("B", "C", 3.0, "EA"),
        BomLine("C", "D", 0.5, "KG"),
    ]


@pytest.fixture
def cyclic_bom() -> list[BomLine]:
    return [
        BomLine("A", "B", 1.0, "EA"),
        BomLine("B", "A", 1.0, "EA"),
    ]


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES
