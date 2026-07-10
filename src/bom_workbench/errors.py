"""Exception hierarchy. Everything raised on purpose derives from BomWorkbenchError."""

from __future__ import annotations


class BomWorkbenchError(Exception):
    """Base class for all bom-workbench errors."""


class DataError(BomWorkbenchError):
    """Bad input data; carries the file and (1-based) row where it was found."""

    def __init__(self, message: str, *, file: str | None = None, row: int | None = None) -> None:
        self.file = file
        self.row = row
        where = ""
        if file:
            where = f" [{file}" + (f", row {row}" if row is not None else "") + "]"
        super().__init__(f"{message}{where}")


class CycleError(BomWorkbenchError):
    """The BOM graph contains a cycle; `path` is the offending chain."""

    def __init__(self, path: tuple[str, ...]) -> None:
        self.path = path
        super().__init__("BOM cycle detected: " + " -> ".join(path))


class DepthExceededError(BomWorkbenchError):
    """Explosion went deeper than `max_levels` — almost always a data problem."""

    def __init__(self, max_levels: int) -> None:
        self.max_levels = max_levels
        super().__init__(f"BOM depth exceeds max_levels={max_levels} (possible bad data)")


class UnknownItemError(BomWorkbenchError):
    """The requested item appears nowhere in the given data."""

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Unknown item: {item_id}")
