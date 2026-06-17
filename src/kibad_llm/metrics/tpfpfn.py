"""Collect tp/fp/fn entries, either globally or grouped by record.

Classes:
    TpFpFnCollector: Return tracked tp/fp/fn entries in JSON-serializable form.
    TpFpFnCollectorCollection: Return raw tp/fp/fn entries for multiple fields at once.
"""

from typing import Any

from kibad_llm.metrics.base import MetricWithTpFpFnEntries
from kibad_llm.metrics.collection import MetricCollectionWithFieldDiscoveryAndGrouping


class TpFpFnCollector(MetricWithTpFpFnEntries):
    """Collect tp/fp/fn entries instead of reducing them to scores.

    By default, results are returned as JSON-safe `[record_id, entry]` pairs. With
    `per_record=True`, entries are grouped by record via
    `MetricWithTpFpFnEntries.state_per_record`.

    Attributes:
        per_record: Whether results should be grouped by record instead of returned as global
            tp/fp/fn lists.
    """

    def __init__(self, per_record: bool = False, **kwargs) -> None:
        """Initialize the tp/fp/fn entry collector.

        Args:
            per_record: Whether to group results by record id.

        Keyword Args:
            field: Optional field to extract from dictionary inputs.
            flatten_dicts: Whether nested dictionaries should be flattened before comparison.
            ignore_subfields: Optional subfields to ignore when hashing dictionary values.
            ignore_missing_entries: Whether one-sided empty entries should be skipped.
        """
        super().__init__(**kwargs)
        self.per_record = per_record

    def _to_jsonable(self, value: Any) -> Any:
        """Recursively convert the collector output into JSON-serializable containers.

        Args:
            value: Arbitrary nested collector state.

        Returns:
            `value` converted into dictionaries, lists, and scalar values that can be serialized
            to JSON.
        """
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
        """Return tp/fp/fn entries in a JSON-serializable structure.

        Returns:
            The tracked tp/fp/fn entries either grouped by record id or as global lists.
        """
        if self.per_record:
            return self._to_jsonable(self.state_per_record)
        else:
            return self._to_jsonable(self.state)


class TpFpFnCollectorCollection(MetricCollectionWithFieldDiscoveryAndGrouping[TpFpFnCollector]):
    """Collect raw tp/fp/fn entries for multiple fields at once.

    The collection lazily creates one `TpFpFnCollector` per field and inherits optional dynamic
    field discovery plus grouped-field expansion from
    `MetricCollectionWithFieldDiscoveryAndGrouping`. Nested dict-like fields can therefore be
    expanded into generated field names such as `organism_trends.Amphibien&Wald` before each
    per-field collector is updated.

    Attributes:
        fields: Explicit field names to evaluate, or `None` to discover them dynamically.
        subfield_keys: Optional rules for expanding nested dict-like fields into generated fields.
        subfield_values: Optional rules restricting which nested values are compared after
            expansion.
        metric_kwargs: Keyword arguments forwarded to the per-field `TpFpFnCollector` instances.
    """

    def __init__(
        self,
        **kwargs,
    ) -> None:
        """Initialize a multi-field tp/fp/fn entry collection.

        Keyword Args:
            fields: Optional allowlist of fields to evaluate. If omitted, fields are discovered
                from the union of keys present in each prediction/reference pair.
            subfield_keys: Optional mapping describing how nested entries are split into generated
                fields.
            subfield_values: Optional mapping restricting which nested values are kept after field
                expansion.
            sort_fields: Whether to sort the fields in the output. Defaults to False.
            per_record: Whether each per-field collector should group entries by record id.
            flatten_dicts: Whether nested dictionaries should be flattened before comparison.
            ignore_subfields: Optional subfields to ignore when hashing dictionary payloads.
            ignore_missing_entries: Whether one-sided empty entries should be skipped.
        """
        super().__init__(metric_class=TpFpFnCollector, **kwargs)
