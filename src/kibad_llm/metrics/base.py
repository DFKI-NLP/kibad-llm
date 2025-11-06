from typing import Any

from kibad_llm.metric import Metric


class MetricWithPrepareEntryAsSet(Metric):
    """Base class for metrics that require preparing entries as sets.

    Args:
        field: Optional; If provided, the field to extract from a dict entry.
    """

    def __init__(self, field: str | None = None) -> None:
        self.field = field
        super().__init__()

    def _prepare_entry_as_set(self, entry: Any) -> set:
        """Helper method to convert any prediction or reference value into a set of values.

        Uses the provided field to retrieve the correct values from a given dict if necessary.
        Returns empty set when there is no value.
        Wraps any found values into a set whilst keeping the unique values unaltered

        Args:
            entry: Any kind of data structure to maybe extract from and eventually wrap in a set.
        Returns: A set of whatever relevant value was put in.
        """
        if self.field is not None:
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Expected entry to be a dict when field is set, but got {type(entry)}"
                )
            entry = entry.get(self.field, None)
        if entry is None:
            return set()
        if isinstance(entry, (list, set)):
            return set(entry)
        return {entry}
