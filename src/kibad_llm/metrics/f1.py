"""F1-based metrics for single fields and collections of fields.

Functions:
    _expand_field_by_key_values: Expand one nested field into generated top-level fields keyed by
        selected nested values.

Classes:
    F1MicroSingleFieldMetric: Compute micro-averaged precision, recall, and F1 for one field.
    F1MicroMultipleFieldsMetric: Aggregate single-field F1 metrics across multiple fields.
"""

from collections import defaultdict
from collections.abc import Hashable
from copy import deepcopy
from typing import Any

from pandas import DataFrame

from kibad_llm.metrics.base import MetricWithTpFpFnEntries
from kibad_llm.metrics.collection import MetricCollection


class F1MicroSingleFieldMetric(MetricWithTpFpFnEntries):
    """Compute micro-averaged precision, recall, and F1 for one label field.

    The metric operates on sets and supports optional field extraction, dictionary flattening, and
    ignored subfields via the inherited entry-normalization helpers.

    Warning:
        Because the metric compares sets, duplicate predicted labels are collapsed (per record).
        For example, ``["A", "A", "B"]`` and ``["A", "B"]`` are treated as a perfect match.

    See `MetricWithPrepareEntryAsSet` and `MetricWithTpFpFnEntries` for keyword arguments
    for entry-to-set preparation and tp/fp/fn collection.
    """

    @staticmethod
    def calculate_scores(state_counts: dict[str, int]) -> dict[str, float]:
        """Calculate precision, recall, F1, and support from tp/fp/fn counts.

        Args:
            state_counts: Mapping with the keys ``tp``, ``fp``, and ``fn``.

        Returns:
            A dictionary containing ``precision``, ``recall``, ``f1``, and ``support``.
        """
        tp, fp, fn = state_counts["tp"], state_counts["fp"], state_counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
        }

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Compute the metric result from the accumulated tp/fp/fn entry state.

        Returns:
            A dictionary containing ``precision``, ``recall``, ``f1``, and ``support``.
        """
        return self.calculate_scores(state_counts=self.state_count)


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
        - a deep-copied entry in which ``field`` has been removed and replaced by one or more
          generated top-level fields such as ``f"{field}.A&B"``
        - the set of generated field names

        The payload of each generated field consists of either all remaining key-value pairs of
        each nested dict, or only those listed in ``value_entries`` if it is provided.

    Raises:
        TypeError: If ``field`` contains values that are neither a dictionary nor a list/set of
            dictionaries while ``key_entries`` are configured.
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


class F1MicroMultipleFieldsMetric(MetricCollection[F1MicroSingleFieldMetric]):
    """Compute single-field F1 scores for multiple fields plus aggregate views.

    The metric instantiates one `F1MicroSingleFieldMetric` per field, optionally expanding nested
    list/dict fields into generated field names such as ``organism_trends.Amphibien&Wald``.

    Attributes:
        fields: Explicit field names to evaluate, or `None` to discover them dynamically.
        format_as_markdown: Whether `_format_result` should render markdown tables.
        subfield_keys: Optional rules for expanding nested dict-like fields into generated fields.
        subfield_values: Optional rules restricting which nested values are compared after
            expansion.
        metric_kwargs: Keyword arguments forwarded to the per-field metrics.

    Methods:
        ignore_missing_entries: Expose whether one-sided empty entries are ignored.
    """

    def __init__(
        self,
        fields: list[str] | None = None,
        format_as_markdown: bool = True,
        subfield_keys: dict[str, list[str]] | None = None,
        subfield_values: dict[str, list[str]] | None = None,
        sort_fields: bool = False,
        **kwargs,
    ) -> None:
        """Initialize a multi-field F1 metric collection.

        Args:
            fields: List of fields to compute `F1MicroSingleFieldMetric` for. If not provided,
                the metric will be computed for all fields found in the data.
            format_as_markdown: Whether to format the result as a markdown table. Defaults to True.
            subfield_keys: Optional dict mapping field names to lists of keys used to split
                dict-like entries into separate generated fields. For a configured field, the
                values of these keys are removed from each nested dict and appended to the field
                name, while the remaining key-value pairs are scored as that generated field's
                payload. This makes it possible to compute metrics separately for entries such as
                ``field1.A&B`` and ``field1.C&D`` instead of scoring the whole original field as
                one unit.
            subfield_values: Optional dict mapping field names to lists of keys that should be
                retained as the payload of generated fields after extracting ``subfield_keys``.
                This allows restricting evaluation to selected nested values, e.g. scoring only
                ``Antwortvariable`` or only ``Antwortvariable`` and ``Trend`` within each
                generated field.
            sort_fields: Whether to sort the fields in the output. Defaults to False.

        Keyword Args:
            field: Optional field name forwarded to `F1MicroSingleFieldMetric` instances.
            flatten_dicts: Whether nested dictionaries should be flattened before comparison.
            ignore_subfields: Optional subfields to ignore when hashing dictionary payloads.
            ignore_missing_entries: Whether one-sided empty entries should be skipped.

        Raises:
            ValueError: If ``fields`` contains the reserved aggregate labels ``ALL`` or ``AVG``.
        """
        # for now, just raise error if fields contain MICRO or MACRO
        if fields is not None and ("ALL" in fields or "AVG" in fields):
            raise ValueError("Fields cannot contain 'ALL' or 'AVG' as field names.")

        self.fields = fields
        self.subfield_keys = subfield_keys
        self.subfield_values = subfield_values
        self.metric_kwargs = kwargs
        super().__init__(sort_fields=sort_fields)

        self.format_as_markdown = format_as_markdown

    @property
    def ignore_missing_entries(self) -> bool:
        """Return whether one-sided empty entries should be ignored.

        Returns:
            `True` if per-field metrics skip updates where one side normalizes to an empty set.
        """
        return self.metric_kwargs.get("ignore_missing_entries", False)

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Update all relevant per-field metrics with one prediction-reference pair.

        Args:
            prediction: Prediction dictionary, or `None` to treat it as an empty dictionary.
            reference: Reference dictionary, or `None` to treat it as an empty dictionary.
            record_id: Optional record identifier forwarded to the per-field metrics.

        Raises:
            TypeError: If ``prediction`` or ``reference`` is neither a dictionary nor `None`.
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
                self.add_metric(field, F1MicroSingleFieldMetric(field=field, **self.metric_kwargs))

        super()._update(prediction=prediction, reference=reference, record_id=record_id)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Compute per-field scores plus macro and micro aggregates.

        Returns:
            A dictionary containing one result per field plus ``AVG`` and ``ALL`` aggregate rows.
            When ``ignore_missing_entries`` removes every field result, ``AVG`` is an empty
            dictionary.
        """
        result = super()._compute(*args, **kwargs)
        if self.ignore_missing_entries:
            # remove results from metrics with empty states to get correct AVG values and shorten the result
            result = {
                name: field_result
                for name, field_result in result.items()
                if any(self.metrics[name].state_count[key] > 0 for key in ("tp", "fp", "fn"))
            }
        # compute mean for precision, recall, f1 over all fields
        scores_list = defaultdict(list)
        for field_result in result.values():
            for key, value in field_result.items():
                scores_list[key].append(value)
        result["AVG"] = {key: sum(values) / len(values) for key, values in scores_list.items()}

        # compute micro average over all instances based on states of all sub-metrics
        state_total = {
            "tp": sum(metric.state_count["tp"] for metric in self.metrics.values()),
            "fp": sum(metric.state_count["fp"] for metric in self.metrics.values()),
            "fn": sum(metric.state_count["fn"] for metric in self.metrics.values()),
        }
        result["ALL"] = F1MicroSingleFieldMetric.calculate_scores(state_counts=state_total)
        return result

    def _format_result(self, result: dict[str, Any]) -> str:
        """Format computed results as markdown or pretty-printed JSON.

        Args:
            result: The result dictionary to format.

        Returns:
            A human-readable string representation of ``result``.
        """
        if self.format_as_markdown:
            # create pandas DataFrame and convert to markdown table
            df = DataFrame.from_dict(result, orient="index")
            df.index.name = "field"
            # round to 3 decimal places
            df = df.round(3)
            return df.to_markdown()
        else:
            return super()._format_result(result)
