from collections import Counter, defaultdict
from typing import Any

from .base import extract_from_text_lenient


def _majority_vote(values: list) -> Any:
    """Return the majority value from a list of values. Returns None on ties."""
    if len(values) == 0:
        raise ValueError("Cannot perform majority vote on empty list")
    value_counts = Counter(values)
    most_common = value_counts.most_common()
    top_value, top_count = most_common[0]
    # Check for tie: any other value with same top_count
    if any(c == top_count for _, c in most_common[1:]):
        return None
    return top_value


def _make_hashable_simple(value: Any) -> Any:
    if isinstance(value, (list, set)):
        # sort and remove None values
        return tuple(sorted(_make_hashable_simple(v) for v in value if v is not None))
    if isinstance(value, tuple):
        # keep order and None values
        return tuple(_make_hashable_simple(v) for v in value)
    if isinstance(value, dict):
        # sort and remove None values
        return tuple(
            sorted((k, _make_hashable_simple(v)) for k, v in value.items() if v is not None)
        )
    return value


def _multi_entry_majority_vote(values: list[list | None], n: int | None = None) -> list:
    """Return the majority items from a list of lists.

    An item is included in the result if it appears in more than half of the lists.

    Works with lists of primitive types, lists of lists, and lists of dicts. Items that are
    None are ignored.

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
            # if the list contains lists or dicts, we need to keep track of the type ...
            if any(isinstance(item, list) for item in vs):
                entry_type = list
            elif any(isinstance(item, dict) for item in vs):
                entry_type = dict
            # ... and make items hashable
            v_hashable = (_make_hashable_simple(item) for item in vs if item is not None)
            item_counts.update(v_hashable)
    majority_items = [item for item, count in item_counts.items() if count > n / 2]
    # convert back to original types (but nested structures remain hashable tuples!)
    if entry_type is list:
        majority_items = [list(item) for item in majority_items]
    elif entry_type is dict:
        majority_items = [dict(item) for item in majority_items]
    elif entry_type is None:
        # all items are primitive types
        pass
    else:
        raise ValueError(f"Unsupported entry type in multi-entry majority vote: {entry_type}")
    return majority_items


def _aggregate_structured_outputs(
    structured_outputs: list[dict | None], skip_type_mismatches: bool = False
) -> dict[str, Any] | None:
    """Aggregate structured outputs from multiple extractions.

    Entries with the same key are aggregated based on their value types:
    - Primitive types (str, int, float, bool): majority vote
    - List types: majority vote per item
    - Dict types: Not yet implemented (raises ValueError)

    Args:
        structured_outputs: list of structured outputs from multiple extractions
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
    Returns:
        aggregated structured output or None if all entries are None
    """
    if all(res is None for res in structured_outputs):
        return None

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
                    _make_hashable_simple(v) if v is not None else None for v in values
                ]
                majority = _majority_vote(values_hashable)
                # convert back to dict
                aggregated[key] = dict(majority) if majority is not None else None
            elif issubclass(value_type, list):
                # multi-value: majority vote per item for list types
                # explicitly pass the number of structured outputs since some values may
                # be None and thus not in current values
                aggregated[key] = _multi_entry_majority_vote(values, n=len(structured_outputs))
            else:
                raise ValueError(f"Unsupported value type for aggregation: {value_type}")

    return aggregated


class RepeatingExtractor:
    """Extractor that repeats extraction multiple times and aggregates results per key.

    This extractor calls the base extraction function multiple times (n times) on the same
    input text and aggregates the structured outputs. The aggregation is done by majority vote
    for primitive types and list types.

    Args:
        n: Number of repetitions (default: 3)
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
        **kwargs: Additional keyword arguments passed to the base extraction function.
    """

    def __init__(self, n: int = 3, skip_type_mismatches: bool = False, **kwargs):
        if n < 1:
            raise ValueError("n must be at least 1")
        self.n = n
        self.skip_type_mismatches = skip_type_mismatches
        self.default_kwargs = kwargs

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        results = []
        for i in range(self.n):
            current_result = extract_from_text_lenient(*args, **combined_kwargs)
            results.append(current_result)

        response_contents = [v.get("response_content", None) for v in results]
        structured_outputs = [v.get("structured", None) for v in results]
        errors = [v.get("error", None) for v in results]
        aggregated_structured = _aggregate_structured_outputs(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )

        result = {
            "response_content_list": response_contents,
            "structured_list": structured_outputs,
            "error_list": errors if any(errors) else None,
            "structured": aggregated_structured,
        }
        return result
