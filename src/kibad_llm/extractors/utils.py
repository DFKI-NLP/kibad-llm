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
