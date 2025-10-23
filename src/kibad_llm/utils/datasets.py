from __future__ import annotations

from collections.abc import Callable
from typing import Any


def wrap_map_func(func, result_key: str) -> Callable:
    """Wrapper to adapt functions to datasets map interface."""

    def wrapper(*args, **kwargs) -> dict[str, Any]:
        return {result_key: func(*args, **kwargs)}

    return wrapper
