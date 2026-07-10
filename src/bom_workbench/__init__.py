"""bom-workbench — BOM/MRP data toolkit over plain CSV.

Multi-level BOM explosion, where-used lookup, and production-plan churn
analysis. Zero runtime dependencies; the CLI entry point is ``bomwb``.
"""

from .churn import diff_plans
from .errors import (
    BomWorkbenchError,
    CycleError,
    DataError,
    DepthExceededError,
    UnknownItemError,
)
from .explode import explode, summarize
from .loaders import load_bom, load_items, load_plan
from .models import (
    BomLine,
    ChurnRow,
    ChurnSummary,
    ExplosionRow,
    Item,
    PlanRow,
    WhereUsedRow,
)
from .where_used import where_used

__version__ = "0.1.0"

__all__ = [
    "BomLine",
    "BomWorkbenchError",
    "ChurnRow",
    "ChurnSummary",
    "CycleError",
    "DataError",
    "DepthExceededError",
    "ExplosionRow",
    "Item",
    "PlanRow",
    "UnknownItemError",
    "WhereUsedRow",
    "__version__",
    "diff_plans",
    "explode",
    "load_bom",
    "load_items",
    "load_plan",
    "summarize",
    "where_used",
]
