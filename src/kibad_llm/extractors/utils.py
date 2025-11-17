from collections import defaultdict
from typing import Any


def make_hashable_simple(value: Any) -> Any:
    if isinstance(value, (list, set)):
        # sort and remove None values
        return tuple(sorted(make_hashable_simple(v) for v in value if v is not None))
    if isinstance(value, tuple):
        # keep order and None values
        return tuple(make_hashable_simple(v) for v in value)
    if isinstance(value, dict):
        # sort and remove None values
        return tuple(
            sorted((k, make_hashable_simple(v)) for k, v in value.items() if v is not None)
        )
    return value


def collect_values_and_type_per_key(
    structured_outputs: list[dict | None], skip_type_mismatches: bool = False
) -> tuple[dict[str, list], dict[str, type | None]]:
    """Collect values and types per key from structured outputs.

    Args:
        structured_outputs: list of structured outputs from multiple extractions
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
    Returns:
        tuple of:
            - dict mapping keys to list of values
            - dict mapping keys to their consistent type (or None if all values are None)
    """
    # collect all keys to correctly handle missing entries
    all_keys: set[str] = set()
    for res in structured_outputs:
        if res is not None:
            all_keys.update(res.keys())
    values_per_key = defaultdict(list)
    type_per_key: dict[str, type | None] = dict()
    # get values and type per key
    for res in structured_outputs:
        if res is not None:
            for key in all_keys:
                value = res.get(key, None)
                values_per_key[key].append(value)
                if value is not None:
                    if key not in type_per_key:
                        type_per_key[key] = type(value)
                    else:
                        if type_per_key[key] != type(value):
                            if not skip_type_mismatches:
                                raise ValueError(
                                    f"Inconsistent types for key '{key}': "
                                    f"{type_per_key[key]} vs {type(value)}"
                                )
                            else:
                                type_per_key[key] = None
    return values_per_key, type_per_key
