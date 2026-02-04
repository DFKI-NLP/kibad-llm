from typing import Any

from .aggregation_utils import aggregate_single_unanimous_multi_union
from .base import extract_from_text_lenient


class UnionExtractor:
    """Extractor that repeats extraction multiple times and aggregates results per key.

    This extractor calls the base extraction function multiple times (for each entry in overrides)
    on the same input text and aggregates the structured outputs. The aggregation is done by union
    for list types and by ensuring consistency for single-value types.

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
        aggregated_structured = aggregate_single_unanimous_multi_union(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]
        return result
