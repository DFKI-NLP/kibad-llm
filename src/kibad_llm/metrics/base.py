"""Helpers and reusable metric base classes for set-based comparisons.

Functions:
    _convert_dict_to_tuple: Convert dictionaries into hashable tuples while dropping ignored keys
        and `None` values.

Classes:
    MetricWithPrepareEntryAsSet: Normalize metric inputs into comparable sets.
    MetricWithTpFpFnEntries: Track tp/fp/fn entries per record for downstream metrics.
"""

from collections.abc import Hashable
import logging
from typing import Any, cast

from kibad_llm.metric import Metric
from kibad_llm.utils.dictionary import flatten_dict_simple

logger = logging.getLogger(__name__)


def _convert_dict_to_tuple(d: dict, ignore_keys: list | None = None) -> tuple:
    """Convert a dictionary into a sorted, hashable tuple.

    Args:
        d: Dictionary to convert.
        ignore_keys: Optional keys that should be excluded from the output.

    Returns:
        A tuple of sorted ``(key, value)`` pairs with `None` values and ignored keys removed.
    """
    _ignore_keys = ignore_keys or []
    return tuple(sorted((k, v) for k, v in d.items() if v is not None and k not in _ignore_keys))


class MetricWithPrepareEntryAsSet(Metric):
    """Base class for metrics that normalize entries into sets before comparison.

    Attributes:
        field: Optional field name extracted from dictionary inputs before comparison.
        flatten_dicts: Whether dictionary inputs are flattened before field extraction.
        ignore_subfields: Subfield names ignored when converting dictionary values into hashable
            tuples.

    Methods:
        _prepare_entry_as_set: Normalize one prediction or reference entry into a set.
    """

    def __init__(
        self,
        field: str | None = None,
        flatten_dicts: bool = False,
        ignore_subfields: dict[str, list] | None = None,
    ) -> None:
        """Initialize the shared entry-normalization settings.

        Args:
            field: Optional field to extract from dictionary inputs.
            flatten_dicts: Whether to flatten nested dictionaries before further processing.
            ignore_subfields: Optional mapping from field names to subfield names that should be
                ignored when converting dictionaries into tuples.
        """
        self.field = field
        self.ignore_subfields = []
        self.flatten_dicts = flatten_dicts
        if ignore_subfields is not None and self.field is not None:
            self.ignore_subfields = ignore_subfields.get(self.field, [])
        super().__init__()

    def _prepare_entry_as_set(self, entry: Any) -> set:
        """Convert one prediction or reference entry into a comparable set.

        If configured, the method first flattens dictionary inputs and/or extracts ``self.field``.
        It then normalizes scalars, dictionaries, lists, and sets into a set representation while
        dropping `None` values.

        Args:
            entry: Value to normalize.

        Returns:
            A set containing the normalized comparable values.

        Raises:
            ValueError: If ``self.field`` is configured but ``entry`` is not a dictionary.
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
            result = {cast(Hashable, entry)}

        return result


class MetricWithTpFpFnEntries(MetricWithPrepareEntryAsSet):
    """Base class for metrics that retain tp/fp/fn entries instead of only counts.

    Attributes:
        ignore_missing_entries: Whether updates with an empty prediction or reference side should
            be skipped.
        state: Mapping from ``tp``, ``fp``, and ``fn`` to sets of ``(record_id, entry)`` pairs.

    Methods:
        reset: Clear the tracked entries and seen record ids.
        state_count: Return tp/fp/fn counts derived from the tracked entries.
        state_per_record: Group tracked entries by record id.
    """

    def __init__(self, ignore_missing_entries: bool = False, **kwargs) -> None:
        """Initialize tp/fp/fn entry tracking.

        Args:
            ignore_missing_entries: If `True`, skip updates where either side normalizes to an
                empty set.

        Keyword Args:
            field: Optional field to extract from dictionary inputs.
            flatten_dicts: Whether to flatten nested dictionaries before further processing.
            ignore_subfields: Optional mapping from field names to subfield names that should be
                ignored when converting dictionaries into tuples.
        """
        super().__init__(**kwargs)
        self.ignore_missing_entries = ignore_missing_entries
        self.reset()

    def reset(self) -> None:
        """Reset the tracked tp/fp/fn entries and the set of seen record ids."""
        self.state: dict[str, set] = {"tp": set(), "fp": set(), "fn": set()}
        self._used_record_ids: set[Hashable] = set()

    @property
    def state_count(self) -> dict[str, int]:
        """Return tp/fp/fn counts derived from the current entry state.

        Returns:
            A mapping with the keys ``tp``, ``fp``, and ``fn`` and the number of tracked entries
            for each category.
        """
        return {key: len(value) for key, value in self.state.items()}

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Update the tp/fp/fn state with one prediction-reference pair.

        Args:
            prediction: Prediction value to normalize and compare.
            reference: Reference value to normalize and compare.
            record_id: Optional record identifier used to keep entries from different records
                separate.

        Warns:
            A warning is logged when ``record_id`` is `None` and an integer id is generated.

        Raises:
            ValueError: If field extraction is configured and either input is not a dictionary.
        """
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
        """Group the current tp/fp/fn state by record id.

        Returns:
            A nested mapping from record id to a dictionary with the keys ``tp``, ``fp``, and
            ``fn`` and sets of entries for that record.
        """
        result: dict[Hashable, dict[str, set]] = {}
        for key, values in self.state.items():
            for record_id, value in values:
                if record_id not in result:
                    result[record_id] = {"tp": set(), "fp": set(), "fn": set()}
                result[record_id][key].add(value)
        return result
