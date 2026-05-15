"""Collect tp/fp/fn entries, raw or grouped by record."""

from copy import deepcopy

from kibad_llm.metrics.base import MetricWithTpFpFnEntries


class TpFpFnCollector(MetricWithTpFpFnEntries):
    """Collect tp/fp/fn entries instead of reducing them to scores.

    By default, results are returned as raw ``(record_id, entry)`` tuples. With ``per_record=True``,
    entries are grouped by record via `MetricWithTpFpFnEntries.state_per_record`.
    """

    def __init__(self, per_record: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.per_record = per_record

    def _compute(self, *args, **kwargs) -> dict:
        """Return raw tp/fp/fn entries, optionally grouped by record."""
        if self.per_record:
            return self.state_per_record
        else:
            # deepcopy to protect against unintended state modification
            return deepcopy(self.state)
