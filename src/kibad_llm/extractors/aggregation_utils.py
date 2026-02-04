from collections import Counter, defaultdict
from typing import Any


class AggregationError(ValueError):
    """Raised when aggregation of structured outputs fails due to conflicts or inconsistencies."""

    pass


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


def _majority_vote(values: list) -> Any:
    """Return the majority value from a list of values. Returns None on ties."""
    if len(values) == 0:
        raise AggregationError("Cannot perform majority vote on empty list")
    value_counts = Counter(values)
    most_common = value_counts.most_common()
    top_value, top_count = most_common[0]
    # Check for tie: any other value with same top_count
    if any(c == top_count for _, c in most_common[1:]):
        return None
    return top_value


def _multi_entry_majority_vote(values: list[list | None], n: int | None = None) -> list:
    """Return the majority items from a list of lists.

    An item is included in the result if it appears in more than half of the lists.

    Works with lists of primitive types, and lists of dicts. Items that are None are ignored.

    Args:
        values: list of lists (or None)
        n: total number of lists (if None, uses len(values))
    Returns:
        list of majority items
    """
    if n is None:
        n = len(values)
    item_counts: Counter = Counter()
    entry_type: type | None = None
    for vs in values:
        if vs is not None:
            # if the list contains dicts, we need to keep track of that ...
            if any(isinstance(item, dict) for item in vs):
                entry_type = dict
            # ... and make items hashable
            v_hashable = (make_hashable_simple(item) for item in vs if item is not None)
            item_counts.update(v_hashable)
    majority_items = [item for item, count in item_counts.items() if count > n / 2]
    # convert back to original types (but nested structures remain hashable tuples!)
    # TODO: use mapping to get original dicts instead of reconstructing
    if entry_type is dict:
        majority_items = [dict(item) for item in majority_items]
    elif entry_type is None:
        # all items are primitive types
        pass
    else:
        raise NotImplementedError(
            f"Unsupported entry type in multi-entry majority vote: {entry_type}"
        )
    return majority_items


def aggregate_majority_vote(
    structured_outputs: list[dict | None], skip_type_mismatches: bool = False
) -> dict[str, Any] | None:
    """Aggregate structured outputs from multiple extractions.

    Entries with the same key are aggregated based on their value types:
    - Primitive types (str, int, float, bool): majority vote
    - Dict types: majority vote
    - List types: majority vote per item

    Args:
        structured_outputs: list of structured outputs from multiple extractions
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
    Returns:
        aggregated structured output or None if all entries are None
    """
    if all(res is None for res in structured_outputs):
        return None

    values_per_key, type_per_key = collect_values_and_type_per_key(
        structured_outputs, skip_type_mismatches=skip_type_mismatches
    )

    aggregated: dict[str, Any] = dict()
    for key, values in values_per_key.items():
        value_type = type_per_key.get(key, None)
        if value_type is None:
            # if all values are None
            aggregated[key] = None
        else:
            # Aggregate based on type
            if issubclass(value_type, (str, int, float, bool)):
                # single-value: majority vote for primitive types
                aggregated[key] = _majority_vote(values)
            elif issubclass(value_type, dict):
                # single-value: majority vote for dicts
                values_hashable = [
                    make_hashable_simple(v) if v is not None else None for v in values
                ]
                majority = _majority_vote(values_hashable)
                # convert back to dict
                aggregated[key] = dict(majority) if majority is not None else None
                # TODO: use mapping to get original dicts instead of reconstructing
                #  mapping = dict(zip(values_hashable, values))
                #  aggregated[key] = mapping[majority] if majority is not None else None
            elif issubclass(value_type, list):
                # multi-value: majority vote per item for list types
                # explicitly pass the number of structured outputs since some values may
                # be None and thus not in current values
                # TODO: review if this is really correct (I have the feeling we should not provide n here)
                aggregated[key] = _multi_entry_majority_vote(values, n=len(structured_outputs))
            else:
                raise NotImplementedError(f"Unsupported value type for aggregation: {value_type}")

    return aggregated


def _aggregate_unanimous(values: list) -> Any:
    """Return a single value if all non-None values in the list are identical.

    This function is used to aggregate values that should be the same across multiple
    extractions. It ensures consistency by raising an error when conflicting values
    are found.

    Args:
        values: List of values to check for consistency

    Returns:
        The single consistent value, or None if all values are None

    Raises:
        AggregationError: If the list contains multiple different non-None values
    """

    # if only None or empty list, return None
    if all(v is None for v in values):
        return None
    # filter out None values
    values = [v for v in values if v is not None]
    if len(set(values)) == 1:
        return values[0]
    raise AggregationError(f"Conflicting values for union with single entry: {set(values)}")


def _multi_entry_union(values: list[list | None]) -> list:
    """Return the union of all items from multiple lists.

    Combines items from all input lists, removing duplicates. Works with lists containing
    primitive types or dictionaries. None values (both None lists and None items within
    lists) are filtered out.

    Args:
        values: List of lists to union, where individual lists can be None

    Returns:
        Sorted list of unique items from all input lists
    """
    item_set: set = set()
    entry_type: type | None = None
    for vs in values:
        if vs is not None:
            # if the list contains dicts, we need to keep track of that ...
            if any(isinstance(item, dict) for item in vs):
                entry_type = dict
            # ... and make items hashable
            v_hashable = (make_hashable_simple(item) for item in vs if item is not None)
            item_set.update(v_hashable)
    # convert back to original types
    # TODO: use mapping to get original dicts instead of reconstructing
    if entry_type is dict:
        return [dict(item) for item in sorted(item_set)]
    else:
        return sorted(item_set)


def aggregate_unanimous_union(
    structured_outputs: list[dict | None], skip_type_mismatches: bool = False
) -> dict[str, Any] | None:
    """Aggregate structured outputs from multiple extractions.

    Entries with the same key are aggregated based on their value types:
    - Primitive types (str, int, float, bool): return value if all extractions agree, else raise AggregationError
    - Dict types: return value if all extractions agree, else raise AggregationError
    - List types: union of all items across extractions

    Args:
        structured_outputs: list of structured outputs from multiple extractions
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
    Returns:
        aggregated structured output or None if all entries are None
    """
    if all(res is None for res in structured_outputs):
        return None

    values_per_key, type_per_key = collect_values_and_type_per_key(
        structured_outputs, skip_type_mismatches=skip_type_mismatches
    )

    aggregated: dict[str, Any] = dict()
    for key, values in values_per_key.items():
        value_type = type_per_key.get(key, None)
        if value_type is None:
            # if all values are None
            aggregated[key] = None
        else:
            # Aggregate based on type
            if issubclass(value_type, (str, int, float, bool)):
                # single-value: this should be identical across all outputs, raises AggregationError if not
                aggregated[key] = _aggregate_unanimous(values)
            elif issubclass(value_type, dict):
                # single-value: this should be identical across all outputs, raises AggregationError if not
                # make dicts hashable for comparison
                values_hashable = [
                    make_hashable_simple(v) if v is not None else None for v in values
                ]
                majority = _aggregate_unanimous(values_hashable)
                # convert back to dict
                # TODO: use mapping to get original dicts instead of reconstructing
                # mapping = dict(zip(values_hashable, values))
                # aggregated[key] = mapping[majority] if majority is not None else None
                aggregated[key] = dict(majority) if majority is not None else None
            elif issubclass(value_type, list):
                # multi-value: union per item for list types
                aggregated[key] = _multi_entry_union(values)
            else:
                raise NotImplementedError(f"Unsupported value type for aggregation: {value_type}")

    return aggregated
