"""Metric collections and helpers for dynamic per-field evaluation.

Functions:
    _expand_field_by_key_values: Expand nested dict-like fields into generated top-level fields.

Classes:
    MetricCollection: Aggregate multiple child metrics behind one metric interface.
    MetricCollectionWithFieldDiscoveryAndGrouping: Lazily create per-field metrics while
        discovering or expanding fields.
"""

from collections.abc import Hashable
from copy import deepcopy
from typing import Any, Generic, TypeVar

from kibad_llm.metric import Metric
from kibad_llm.metrics.base import SingleFieldMetric

T = TypeVar("T", bound=Metric)


class MetricCollection(Metric, Generic[T]):
    """A metric that aggregates multiple sub-metrics."""

    def __init__(self, metrics: dict[str, T] | None = None, sort_fields: bool = False) -> None:
        """Initialize the metric collection.

        Args:
            metrics: Optional mapping of metric names to metric instances.
            sort_fields: Whether computed results should be emitted in sorted field order.
        """
        super().__init__()
        self.metrics: dict[str, T] = metrics or dict()
        self.sort_fields = sort_fields

    def add_metric(self, name: str, metric: T) -> None:
        """Adds a new metric to the collection."""
        if name in self.metrics:
            raise ValueError(f"Metric {name} already exists")
        self.metrics[name] = metric

    def reset(self) -> None:
        """Resets all sub-metrics."""
        for metric in self.metrics.values():
            metric.reset()

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Updates all sub-metrics with the given data."""
        for metric in self.metrics.values():
            metric.update(prediction=prediction, reference=reference, record_id=record_id)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes and returns the results of all sub-metrics.

        Returns:
            A dictionary mapping metric names to their computed results.
        """
        results = {}
        names = list(self.metrics.keys())
        if self.sort_fields:
            names = sorted(names)
        for name in names:
            results[name] = self.metrics[name].compute(*args, reset=False, **kwargs)
        return results


def _expand_field_by_key_values(
    entry: dict, field: str, key_entries: list, value_entries: list | None = None
) -> tuple[dict[str, Any], set[str]]:
    """Replace one dict-like field with generated top-level fields keyed by selected values.

    Args:
        entry: Mapping that contains the field to expand.
        field: Name of the field whose value must be either a dict or a list/set of dicts.
        key_entries: Keys whose values are removed from each nested dict and concatenated to
            form the generated field names.
        value_entries: Optional keys to retain as the payload of each generated field after the
            key values have been extracted. If not provided, all remaining key-value pairs are kept.

    Returns:
        A tuple containing:
        - a deep-copied entry in which `field` has been removed and replaced by one or more
          generated top-level fields such as `f"{field}.A&B"`
        - the set of generated field names

        The payload of each generated field consists of either all remaining key-value pairs of
        each nested dict, or only those listed in `value_entries` if it is provided.
    """

    entry = deepcopy(entry)
    field_value = entry.pop(field, None)

    # a single dict
    if isinstance(field_value, dict):
        key_values = []
        for key in key_entries:
            key_values.append(str(field_value.pop(key, None)))
        new_field = f"{field}." + "&".join(key_values)
        if value_entries is not None:
            field_value = {
                value_entry: field_value[value_entry]
                for value_entry in value_entries
                if value_entry in field_value
            }
        entry[new_field] = field_value
        return entry, {new_field}

    # multiple entries of dicts
    elif isinstance(field_value, (list, set)):
        if not all(isinstance(e, dict) for e in field_value):
            raise TypeError(
                f"Field {field} contains non-dict entries, but subfield_keys are provided."
            )

        new_fields = set()
        for f_value in field_value:
            key_values = []
            for key in key_entries:
                key_values.append(str(f_value.pop(key, None)))
            new_field = f"{field}." + "&".join(key_values)
            if new_field not in entry:
                entry[new_field] = []
            if value_entries is not None:
                f_value = {
                    value_entry: f_value[value_entry]
                    for value_entry in value_entries
                    if value_entry in f_value
                }
            entry[new_field].append(f_value)
            new_fields.add(new_field)
        for new_field in new_fields:
            entry[new_field] = type(field_value)(entry[new_field])
        return entry, new_fields

    if field_value is None:
        return entry, set()

    else:
        raise TypeError(
            f"Field {field} is neither a dict nor a list of dicts, but subfield_keys are provided."
        )


T2 = TypeVar("T2", bound=SingleFieldMetric)


class MetricCollectionWithFieldDiscoveryAndGrouping(MetricCollection[T2], Generic[T2]):
    """A metric collection that discovers fields dynamically and can group nested entries.

    This collection creates per-field metrics lazily during `_update`. Fields can either
    be taken from an explicit allowlist or, on each update, discovered from the union of
    prediction and reference keys. Additionally, configured dict-like fields can be expanded
    into generated top-level fields such as `field.A&B` before the underlying single-field
    metrics are updated. During that expansion, the configured grouping keys are used to derive
    the generated field names and are removed from the scored payload, while `subfield_values`
    can optionally restrict which of the remaining nested values are compared. Additional keyword
    arguments passed to `__init__` are forwarded to each lazily created per-field metric.
    """

    def __init__(
        self,
        metric_class: type[T2],
        fields: list[str] | None = None,
        subfield_keys: dict[str, list[str]] | None = None,
        subfield_values: dict[str, list[str]] | None = None,
        sort_fields: bool = False,
        field_overrides: dict[str, dict[str, Any]] | None = None,
        **kwargs,
    ) -> None:
        """Initialize the field-discovering metric collection.

        Args:
            metric_class: Metric class used to instantiate field-specific metrics.
            fields: Optional allowlist of fields to evaluate. If omitted, fields are discovered
                from the union of keys present in each prediction/reference pair.
            subfield_keys: Optional mapping describing how nested entries are split into generated
                fields.
            subfield_values: Optional mapping restricting which nested values are kept after field
                expansion.
            sort_fields: Whether computed results should be emitted in sorted field order.
            field_overrides: Optional mapping of field names to keyword arguments for each per-field metric.
            **kwargs: Additional keyword arguments forwarded to each created metric instance.
        """
        self.metric_class = metric_class
        self.fields = fields
        self.subfield_keys = subfield_keys
        self.subfield_values = subfield_values
        self.field_overrides = field_overrides or {}
        self.metric_kwargs = kwargs
        super().__init__(sort_fields=sort_fields)

    def _make_metric(self, field: str) -> T2:
        """Create a new per-field metric instance for `field`."""
        metric_kwargs = self.metric_kwargs.copy()
        metric_kwargs.update(self.field_overrides.get(field, {}))
        return self.metric_class(field=field, **metric_kwargs)

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Normalize entries, discover or expand fields, and update all per-field metrics.

        `None` predictions or references are treated as empty dictionaries. Each update expects
        both inputs to be dict-like so fields can be selected either from `self.fields` or from
        the union of keys present in the current pair of entries.

        If `subfield_keys` is configured for a field, that field is expanded into one or more
        generated top-level fields via `_expand_field_by_key_values` before metrics are
        looked up or created. Any missing per-field metric is instantiated lazily using
        `self.metric_class` and then updated through `MetricCollection`.

        Args:
            prediction: Prediction entry for a single record. Must be a dict or `None`.
            reference: Reference entry for a single record. Must be a dict or `None`.
            record_id: Optional record identifier forwarded to all child metrics.

        Raises:
            TypeError: If `prediction` or `reference` is not a dict after `None` values are
                normalized.
        """
        if prediction is None:
            prediction = dict()
        if reference is None:
            reference = dict()
        if not isinstance(prediction, dict) or not isinstance(reference, dict):
            raise TypeError(
                f"Prediction and reference should be dicts, but got {type(prediction)} and {type(reference)}."
            )
        if self.fields is None:
            fields = list(prediction.keys() | reference.keys())
        else:
            fields = self.fields

        if self.subfield_keys is not None:
            new_fields = []
            subfield_values = self.subfield_values or {}
            for field in fields:
                if field in self.subfield_keys:
                    prediction, new_prediction_fields = _expand_field_by_key_values(
                        entry=prediction,
                        field=field,
                        key_entries=self.subfield_keys[field],
                        value_entries=subfield_values.get(field, None),
                    )
                    reference, new_reference_fields = _expand_field_by_key_values(
                        entry=reference,
                        field=field,
                        key_entries=self.subfield_keys[field],
                        value_entries=subfield_values.get(field, None),
                    )
                    new_fields.extend(new_prediction_fields | new_reference_fields)
                else:
                    new_fields.append(field)
            fields = new_fields

        # check if all required metrics exist and create missing ones via self.add_metric
        for field in fields:
            if field not in self.metrics:
                self.add_metric(field, self._make_metric(field))

        super()._update(prediction=prediction, reference=reference, record_id=record_id)
