from collections.abc import Hashable
import logging
from typing import Any

from kibad_llm.metric import Metric
from kibad_llm.utils.dictionary import flatten_dict_simple

logger = logging.getLogger(__name__)


def _convert_dict_to_tuple(d: dict, ignore_keys: list | None = None) -> tuple:
    """Convert a dict to a sorted tuple of its items. Removes None values."""
    _ignore_keys = ignore_keys or []
    return tuple(sorted((k, v) for k, v in d.items() if v is not None and k not in _ignore_keys))


class MetricWithPrepareEntryAsSet(Metric):
    """Base class for metrics that require preparing entries as sets.

    Args:
        field: Optional; If provided, the field to extract from a dict entry.
        flatten_dicts: bool; Whether to flatten dict entries before processing.
        ignore_subfields: Optional; A dict mapping field names to lists of subfield names to ignore
            when converting dicts to tuples.
    """

    def __init__(
        self,
        field: str | None = None,
        flatten_dicts: bool = False,
        ignore_subfields: dict[str, list] | None = None,
    ) -> None:
        self.field = field
        self.ignore_subfields = []
        self.flatten_dicts = flatten_dicts
        if ignore_subfields is not None and self.field is not None:
            self.ignore_subfields = ignore_subfields.get(self.field, [])
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
        if entry is not None and isinstance(entry, dict) and self.flatten_dicts:
            entry = flatten_dict_simple(entry)

        if self.field is not None and entry is not None:
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


class MetricWithTpFpFnEntries(MetricWithPrepareEntryAsSet):
    """Base class for metrics that hold true positive, false positive, and false negative entries (not just counts)."""

    def __init__(self, ignore_missing_entries: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ignore_missing_entries = ignore_missing_entries
        self.reset()
        self._used_record_ids: set[Hashable] = set()

    def reset(self) -> None:
        """Resets all values of the internal state."""
        self.state: dict[str, set] = {"tp": set(), "fp": set(), "fn": set()}

    @property
    def state_count(self) -> dict[str, int]:
        """A dict mapping field names to how many times each entry was seen."""
        return {key: len(value) for key, value in self.state.items()}

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Updates the internal state with the given prediction(s) and reference(s)."""
        prediction_set = self._prepare_entry_as_set(prediction)
        reference_set = self._prepare_entry_as_set(reference)
        if self.ignore_missing_entries and (len(prediction_set) == 0 or len(reference_set) == 0):
            return

        if record_id is None:
            int_record_ids = {r_id for r_id in self._used_record_ids if isinstance(r_id, int)}
            max_record_id = max(int_record_ids) if int_record_ids else 0
            record_id = max_record_id + 1
            logger.warning(
                f"Record ID is None. Assuming the entries belong to a new record (generated record id: {record_id})."
            )
        self._used_record_ids.add(record_id)

        # prepend the record_id to not merge entries over records
        prediction_set_with_record_id = {(record_id, entry) for entry in prediction_set}
        reference_set_with_record_id = {(record_id, entry) for entry in reference_set}

        self.state["tp"].update(prediction_set_with_record_id & reference_set_with_record_id)
        self.state["fp"].update(prediction_set_with_record_id - reference_set_with_record_id)
        self.state["fn"].update(reference_set_with_record_id - prediction_set_with_record_id)

    @property
    def state_per_record(self) -> dict[Hashable, dict[str, set]]:
        """A dict mapping record ids to dicts that map field names to sets of entries for that record."""
        result: dict[Hashable, dict[str, set]] = {}
        for key, values in self.state.items():
            for record_id, value in values:
                if record_id not in result:
                    result[record_id] = {"tp": set(), "fp": set(), "fn": set()}
                result[record_id][key].add(value)
        return result