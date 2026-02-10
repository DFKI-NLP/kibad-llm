from typing import Any

from .aggregation_utils import aggregate_majority_vote
from .base import extract_from_text_lenient
from ..llms import VllmInProcess


class EnsembleExtractor:
    """Extractor that repeats extraction multiple times and aggregates results per key.

    This extractor calls the base extraction function multiple times for each entry in overrides,
    repeats this process multiple times and aggregates the structured outputs. The aggregation is
    done by majority vote for primitive types and list types.

    Args:
        n: Number of repetitions per override (default: None, which means 1 repetition per override)
        overrides: A list of dictionaries containing parameter overrides for each extraction (default: None,
            which means no overrides and just one extraction per repetition)
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
        return_as_list: List of field names to return as lists of all extracted values
            (default: None)
        **kwargs: Additional keyword arguments passed to the base extraction function.
    """

    def __init__(
        self,
        overrides: list[dict] | dict[str, dict] | None = None,
        n: int | None = None,
        skip_type_mismatches: bool = False,
        return_as_list: list[str] | None = None,
        **kwargs,
    ):
        if n is not None and n < 1:
            raise ValueError("n must be at least 1")
        if overrides is not None and len(overrides) < 1:
            raise ValueError("overrides must contain at least one set of parameters if provided")
        self.n = n or 1
        if isinstance(overrides, list):
            overrides = {str(i): override for i, override in enumerate(overrides)}
        self.overrides = overrides or {"default": {}}
        self.skip_type_mismatches = skip_type_mismatches
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        results = []
        for override_name, override_params in self.overrides:
            current_kwargs = {**combined_kwargs, **override_params}
            for i in range(self.n):
                current_result = extract_from_text_lenient(*args, **current_kwargs)
                results.append(current_result)
            # delete the llm from override_params to clear memory after each override if it exists,
            # since it can be large (usually just one llm instance fits in memory and multiple
            # overrides with different llm instances can cause OOM)
            llm = override_params.get("llm", None)
            if isinstance(llm, VllmInProcess):
                # llm.destroy() # requires implementation of VllmInProcess.destroy()
                pass

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = aggregate_majority_vote(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )
        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]

        return result
