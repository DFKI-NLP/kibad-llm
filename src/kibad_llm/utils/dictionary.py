from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

logger = logging.getLogger(__name__)


def flatten_dict_simple(d: Mapping[str, Any], sep: str = ".") -> dict[str, Any]:
    """Flatten a dictionary with simple rules:
    - Keep only non-empty primitive values (str, int, float, bool)
    - For lists of primitives, keep as is
    - For lists of dicts, create new keys by combining parent key and child keys,
      and aggregate values into lists (removing duplicates and sorting)

    IMPORTANT: This function does not handle nested dicts beyond one level inside lists.

    Args:
        d: The dictionary to flatten.
        sep: The separator to use when combining keys.
    Returns:
        A flattened dictionary.
    """
    result: dict[str, Any] = dict()
    for k, v in d.items():
        # remove empty values
        if v is None or (isinstance(v, str) and v.strip() == ""):
            pass
        elif isinstance(v, (str, int, float, bool)):
            result[k] = v
        elif isinstance(v, list):
            if all(isinstance(e, (str, int, float, bool)) for e in v):
                result[k] = v
            elif all(isinstance(e, dict) for e in v):
                current_keys = set()
                for e in v:
                    for k2, v2 in e.items():
                        if v2 is not None and not (isinstance(v2, str) and v2.strip() == ""):
                            (
                                result[f"{k}{sep}{k2}"].append(v2)
                                if f"{k}{sep}{k2}" in result
                                else result.setdefault(f"{k}{sep}{k2}", [v2])
                            )
                            current_keys.add(f"{k}{sep}{k2}")
                for k2 in current_keys:
                    result[k2] = sorted(set(result[k2]))
            else:
                raise ValueError(f"Cannot flatten list with mixed types: {v}")

    return result
