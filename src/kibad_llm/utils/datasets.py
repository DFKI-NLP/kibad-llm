"""HuggingFace ``datasets`` adapter utilities.

Currently provides :func:`wrap_map_func`, which wraps an arbitrary callable so its
return value is stored under a single key in the dict expected by ``Dataset.map()``.
Used in :mod:`kibad_llm.predict` to adapt the PDF-reader callable to the datasets map
interface.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def wrap_map_func(func, result_key: str) -> Callable:
    """Wrapper to adapt functions to datasets map interface."""

    def wrapper(*args, **kwargs) -> dict[str, Any]:
        return {result_key: func(*args, **kwargs)}

    return wrapper
