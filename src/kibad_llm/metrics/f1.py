"""F1-based metrics for single fields and collections of fields.

Functions:
    _expand_field_by_key_values: Expand one nested field into generated top-level fields keyed by
        selected nested values.

Classes:
    F1MicroSingleFieldMetric: Compute micro-averaged precision, recall, and F1 for one field.
    F1MicroMultipleFieldsMetric: Aggregate single-field F1 metrics across multiple fields.
"""

from collections import defaultdict
from typing import Any

from pandas import DataFrame

from kibad_llm.metrics.base import MetricWithTpFpFnEntries
from kibad_llm.metrics.collection import MetricCollectionWithFieldDiscoveryAndGrouping


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


class F1MicroMultipleFieldsMetric(
    MetricCollectionWithFieldDiscoveryAndGrouping[F1MicroSingleFieldMetric]
):
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
        format_as_markdown: bool = True,
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
            flatten_dicts: Whether nested dictionaries should be flattened before comparison.
            ignore_subfields: Optional subfields to ignore when hashing dictionary payloads.
            ignore_missing_entries: Whether one-sided empty entries should be skipped.

        Raises:
            ValueError: If ``fields`` contains the reserved aggregate labels ``ALL`` or ``AVG``.
        """
        super().__init__(metric_class=F1MicroSingleFieldMetric, **kwargs)

        # reserve aggregate result field names used by this metric
        if self.fields is not None and ("ALL" in self.fields or "AVG" in self.fields):
            raise ValueError("Fields cannot contain 'ALL' or 'AVG' as field names.")

        self.format_as_markdown = format_as_markdown

    @property
    def ignore_missing_entries(self) -> bool:
        """Return whether one-sided empty entries should be ignored.

        Returns:
            `True` if per-field metrics skip updates where one side normalizes to an empty set.
        """
        return self.metric_kwargs.get("ignore_missing_entries", False)

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
