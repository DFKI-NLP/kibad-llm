from typing import Any

from kibad_llm.metric import Metric


def _convert_dict_to_tuple(d: dict) -> tuple:
    """Convert a dict to a sorted tuple of its items. Removes None values."""
    return tuple(sorted((k, v) for k, v in d.items() if v is not None))


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
        Wraps any found values into a set whilst keeping the unique values unaltered.
        Removes None values.

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
            # convert list entries to tuples (sort each by key to ensure consistent ordering)
            # to make dicts hashable for the set
            maybe_tuples = (
                _convert_dict_to_tuple(e) if isinstance(e, dict) else e
                for e in entry
                if e is not None
            )
            return set(maybe_tuples)
        if isinstance(entry, dict):
            return {_convert_dict_to_tuple(entry)}
        return {entry}
