from typing import Any

from .base import extract_from_text_lenient
from .utils import collect_values_and_type_per_key, make_hashable_simple


def _union_single(values: list) -> Any:
    """Return a single value if all non-None values in the list are identical.

    This function is used to aggregate values that should be the same across multiple
    extractions. It ensures consistency by raising an error when conflicting values
    are found.

    Args:
        values: List of values to check for consistency

    Returns:
        The single consistent value, or None if all values are None

    Raises:
        ValueError: If the list contains multiple different non-None values
    """

    # if only None or empty list, return None
    if all(v is None for v in values):
        return None
    # filter out None values
    values = [v for v in values if v is not None]
    if len(set(values)) == 1:
        return values[0]
    raise ValueError(f"Conflicting values for union with single entry: {set(values)}")


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
    if entry_type is dict:
        return [dict(item) for item in sorted(item_set)]
    else:
        return sorted(item_set)


def _aggregate_structured_outputs_union(
    structured_outputs: list[dict | None], skip_type_mismatches: bool = False
) -> dict[str, Any] | None:
    """Aggregate structured outputs from multiple extractions.

    Entries with the same key are aggregated based on their value types:
    - Primitive types (str, int, float, bool): return value if all extractions agree, else raise ValueError
    - List types: union of all items across extractions
    - Dict types: return value if all extractions agree, else raise ValueError

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
                aggregated[key] = _union_single(values)
            elif issubclass(value_type, dict):
                # single-value: majority vote for dicts
                values_hashable = [
                    make_hashable_simple(v) if v is not None else None for v in values
                ]
                majority = _union_single(values_hashable)
                # convert back to dict
                aggregated[key] = dict(majority) if majority is not None else None
            elif issubclass(value_type, list):
                # multi-value: majority vote per item for list types
                # explicitly pass the number of structured outputs since some values may
                # be None and thus not in current values
                aggregated[key] = _multi_entry_union(values)  # , n=len(structured_outputs))
            else:
                raise ValueError(f"Unsupported value type for aggregation: {value_type}")

    return aggregated


class UnionExtractor:
    """Extractor that repeats extraction multiple times and aggregates results per key.

    This extractor calls the base extraction function multiple times (for each entry in overrides)
    on the same input text and aggregates the structured outputs. The aggregation is done by union
    for primitive types and list types.

    Args:
        overrides: A list of dictionaries containing parameter overrides for each extraction.
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
        return_as_list: List of field names to return as lists of all extracted values
            (default: None)
        **kwargs: Additional keyword arguments passed to the base extraction function.
    """

    def __init__(
        self,
        overrides: list[dict],
        skip_type_mismatches: bool = False,
        return_as_list: list[str] | None = None,
        **kwargs,
    ):
        if len(overrides) < 1:
            raise ValueError("overrides must contain at least one set of parameters")
        self.overrides = overrides
        self.skip_type_mismatches = skip_type_mismatches
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        results = []
        for override_params in self.overrides:
            current_kwargs = {**combined_kwargs, **override_params}
            current_result = extract_from_text_lenient(*args, **current_kwargs)
            results.append(current_result)

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = _aggregate_structured_outputs_union(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]
        return result
