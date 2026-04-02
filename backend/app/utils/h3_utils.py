from collections.abc import Iterable


def validate_h3_cells(cells: Iterable[str]) -> bool:
    parsed = [cell for cell in cells if isinstance(cell, str) and len(cell) >= 5]
    return len(parsed) > 0
