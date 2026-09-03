from typing import Any

from ..llms import VllmInProcess
from .aggregation_utils import Aggregator
from .base import extract_from_text_lenient


class EnsembleExtractor:
    """Extractor that executes extraction for multiple override configs and aggregates results per key.

    This extractor calls the base extraction function multiple times for each entry in overrides
    and aggregates the structured outputs. The aggregation is done by majority vote for primitive
    types and list types (same as in RepeatingExtractor).

    Args:
        overrides: A list of dictionaries containing parameter overrides for each extraction (default: None,
            which means no overrides and just one extraction per repetition)
        vllm_sleep_level: If using vLLM in any of the overrides, the sleep level to put the vLLM to after
            each extraction (default: 2). See https://docs.vllm.ai/en/latest/features/sleep_mode/ for details.
            Setting this to None will disable putting the vLLM to sleep, which can lead to OOM if multiple
            overrides with different vLLM instances are used.
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
        return_as_list: List of field names to return as lists of all extracted values
            (default: None)
        **kwargs: Additional keyword arguments passed to the base extraction function.
    """

    def __init__(
        self,
        aggregator: Aggregator,
        overrides: list[dict] | dict[str, dict] | None = None,
        vllm_sleep_level: int | None = 2,
        return_as_list: list[str] | None = None,
        **kwargs,
    ):
        if overrides is not None and len(overrides) < 1:
            raise ValueError("overrides must contain at least one set of parameters if provided")
        if isinstance(overrides, list):
            overrides = {str(i): override for i, override in enumerate(overrides)}
        self.overrides = overrides or {"default": {}}
        self.aggregator = aggregator
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs
        self.vllm_sleep_level = vllm_sleep_level

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        results = []
        for override_name, override_params in self.overrides.items():
            llm = override_params.get("llm", None)
            if isinstance(llm, VllmInProcess):
                llm.llm.wake_up()

            current_kwargs = {**combined_kwargs, **override_params}
            current_result = extract_from_text_lenient(*args, **current_kwargs)
            results.append(current_result)

            # Put the vllm llm to sleep after each override if it exists, since it
            # can be quite large. Usually, just one llm instance fits in memory and multiple
            # overrides with different llm instances can cause OOM.
            if isinstance(llm, VllmInProcess) and self.vllm_sleep_level is not None:
                llm.llm.sleep(level=self.vllm_sleep_level)

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = self.aggregator(structured_outputs)
        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]

        return result
