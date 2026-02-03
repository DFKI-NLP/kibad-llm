from typing import Any

from .aggregation_utils import _aggregate_structured_outputs
from .base import extract_from_text_lenient


class RepeatingExtractor:
    """Extractor that repeats extraction multiple times and aggregates results per key.

    This extractor calls the base extraction function multiple times (n times) on the same
    input text and aggregates the structured outputs. The aggregation is done by majority vote
    for primitive types and list types.

    Args:
        n: Number of repetitions (default: 3)
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
        return_as_list: List of field names to return as lists of all extracted values
            (default: None)
        **kwargs: Additional keyword arguments passed to the base extraction function.
    """

    def __init__(
        self,
        n: int = 3,
        skip_type_mismatches: bool = False,
        return_as_list: list[str] | None = None,
        **kwargs,
    ):
        if n < 1:
            raise ValueError("n must be at least 1")
        self.n = n
        self.skip_type_mismatches = skip_type_mismatches
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        results = []
        for i in range(self.n):
            current_result = extract_from_text_lenient(*args, **combined_kwargs)
            results.append(current_result)

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = _aggregate_structured_outputs(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )
        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]

        return result
