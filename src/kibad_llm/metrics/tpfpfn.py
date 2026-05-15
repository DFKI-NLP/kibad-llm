"""Collect tp/fp/fn entries, raw or grouped by record."""

from typing import Any

from kibad_llm.metrics.base import MetricWithTpFpFnEntries


class TpFpFnCollector(MetricWithTpFpFnEntries):
    """Collect tp/fp/fn entries instead of reducing them to scores.

    By default, results are returned as JSON-safe ``[record_id, entry]`` pairs. With
    ``per_record=True``, entries are grouped by record via
    `MetricWithTpFpFnEntries.state_per_record`.
    """

    def __init__(self, per_record: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.per_record = per_record

    def _to_jsonable(self, value: Any) -> Any:
        """Recursively convert the collector output into JSON-serializable containers."""
        if isinstance(value, dict):
            return {key: self._to_jsonable(subvalue) for key, subvalue in value.items()}
        if isinstance(value, set):
            return sorted((self._to_jsonable(item) for item in value), key=repr)
        if isinstance(value, tuple):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        return value

    def _compute(self, *args, **kwargs) -> dict:
        """Return tp/fp/fn entries in a JSON-serializable structure."""
        if self.per_record:
            return self._to_jsonable(self.state_per_record)
        else:
            return self._to_jsonable(self.state)
