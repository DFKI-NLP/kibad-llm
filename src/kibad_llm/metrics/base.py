from typing import Any

from kibad_llm.metric import Metric


def _convert_dict_to_tuple(d: dict, ignore_keys: list | None = None) -> tuple:
    """Convert a dict to a sorted tuple of its items. Removes None values."""
    _ignore_keys = ignore_keys or []
    return tuple(sorted((k, v) for k, v in d.items() if v is not None and k not in _ignore_keys))


class MetricWithPrepareEntryAsSet(Metric):
    """Base class for metrics that require preparing entries as sets.

    Args:
        field: Optional; If provided, the field to extract from a dict entry.
        ignore_subfields: Optional; A dict mapping field names to lists of subfield names to ignore
            when converting dicts to tuples.
    """

    def __init__(
        self, field: str | None = None, ignore_subfields: dict[str, list] | None = None
    ) -> None:
        self.field = field
        self.ignore_subfields = []
        if ignore_subfields is not None and field is not None:
            self.ignore_subfields = ignore_subfields.get(field, [])
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
            result = set()
        elif isinstance(entry, (list, set)):
            # convert list entries to tuples (sort each by key to ensure consistent ordering)
            # to make dicts hashable for the set
            maybe_tuples = (
                (
                    _convert_dict_to_tuple(e, ignore_keys=self.ignore_subfields)
                    if isinstance(e, dict)
                    else e
                )
                for e in entry
                if e is not None
            )
            result = set(maybe_tuples)
        elif isinstance(entry, dict):
            result = {_convert_dict_to_tuple(entry, ignore_keys=self.ignore_subfields)}
        else:
            result = {entry}

        return result
