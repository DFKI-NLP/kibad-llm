from collections import Counter, defaultdict
from typing import Any

from .base import extract_from_text


def _majority_vote(values: list) -> Any:
    """Return the majority value from a list of values."""
    if len(values) == 0:
        raise ValueError("Cannot perform majority vote on empty list")
    value_counts = Counter(values)
    majority_value, _ = value_counts.most_common(1)[0]
    return majority_value


def _multi_entry_majority_vote(values: list[list | None], n: int | None = None) -> list:
    """Return the majority items from a list of lists.

    An item is included in the result if it appears in more than half of the lists.

    Args:
        values: list of lists (or None)
        n: total number of lists (if None, uses len(values))
    Returns:
        list of majority items
    """
    if n is None:
        n = len(values)
    item_counts: Counter = Counter()
    for v in values:
        if v is not None:
            item_counts.update(v)
    majority_items = [item for item, count in item_counts.items() if count > n / 2]
    return majority_items


def _aggregate_structured_outputs(
    structured_outputs: list[dict], skip_type_mismatches: bool = False
) -> dict[str, Any]:
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
        aggregated structured output
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

    aggregated: dict[str, Any] = dict()
    for key, values in values_per_key.items():
        value_type = type_per_key.get(key, None)
        if value_type is None:
            # if all values are None
            aggregated[key] = None
        else:
            # Aggregate based on type
            if issubclass(value_type, (str, int, float, bool)):
                # majority vote for primitive types
                aggregated[key] = _majority_vote(values)
            elif issubclass(value_type, list):
                # majority vote per item for list types
                # explicitly pass the number of structured outputs since some values may
                # be None and thus not in current values
                aggregated[key] = _multi_entry_majority_vote(values, n=len(structured_outputs))
            elif issubclass(value_type, dict):
                raise ValueError("Aggregation for dict type values is not yet implemented")
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
            current_result = extract_from_text(*args, **combined_kwargs)
            results.append(current_result)

        response_contents = [v["response_content"] for v in results]
        structured_outputs = [v["structured"] for v in results]
        aggregated_structured = _aggregate_structured_outputs(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )

        return {
            "response_content_list": response_contents,
            "structured_list": structured_outputs,
            "structured": aggregated_structured,
        }
