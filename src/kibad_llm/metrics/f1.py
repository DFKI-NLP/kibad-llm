from collections import defaultdict
from collections.abc import Hashable
from typing import Any

from pandas import DataFrame

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet
from kibad_llm.metrics.collection import MetricCollectionWithFieldDiscoveryAndGrouping


class F1MicroSingleFieldMetric(MetricWithPrepareEntryAsSet):
    """Computes micro averaged precision, recall, and F1 score for single- and multi-label
    classification tasks.

    The metric operates on sets and allows for simple preprocessing, see _prepare_entry for details.

    WARNING:
    !Since the metric operates on sets, this can obfuscate if the LLM produces duplicate labels
    !in multi-label settings. E.g., prediction = ["A", "A", "B"] and reference = ["A", "B"] will
    !be treated as perfect prediction with tp=2, fp=0, fn=0 even though the prediction contains a
    !duplicate label "A".

    Args:
        ignore_missing_entries: If True, instances where either prediction or reference is empty
            will be ignored in the metric calculation.
        **kwargs: Keyword arguments for entry-to-set preparation. See
            `MetricWithPrepareEntryAsSet` for supported options.
    """

    def __init__(self, ignore_missing_entries: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ignore_missing_entries = ignore_missing_entries
        self.reset()

    def reset(self) -> None:
        """Resets all values of the internal state to zero"""
        self.state: dict[str, int] = {"tp": 0, "fp": 0, "fn": 0}

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Updates the internal state with the given prediction(s) and reference(s).
        See `_prepare_entry_as_set` for accepted input formats.
        """
        prediction_set = self._prepare_entry_as_set(prediction)
        reference_set = self._prepare_entry_as_set(reference)
        if self.ignore_missing_entries and (len(prediction_set) == 0 or len(reference_set) == 0):
            return

        self.state["tp"] += len(prediction_set & reference_set)
        self.state["fp"] += len(prediction_set - reference_set)
        self.state["fn"] += len(reference_set - prediction_set)

    @staticmethod
    def calculate_scores(state: dict[str, int]) -> dict[str, float]:
        """Calculates precision, recall and f1 from true positives, false positives and false negatives.

        Args:
            state: dictionary with keys "tp", "fp", "fn"

        returns: dictionary with precision, recall and f1
        """
        tp, fp, fn = state["tp"], state["fp"], state["fn"]
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
        """Computes the micro average of precision, recall and f1 score."""
        return self.calculate_scores(state=self.state)


class F1MicroMultipleFieldsMetric(
    MetricCollectionWithFieldDiscoveryAndGrouping[F1MicroSingleFieldMetric]
):
    """Compute micro-averaged F1 scores for multiple fields plus aggregate summaries.

    This metric applies :class:`F1MicroSingleFieldMetric` to each configured or discovered
    field and augments the per-field results with two aggregate entries:

    - ``AVG``: macro average of the reported scores across fields
    - ``ALL``: micro average computed from the summed true-positive, false-positive, and
      false-negative counts across all field metrics

    Field discovery and optional subfield expansion are inherited from
    :class:`MetricCollectionWithFieldDiscoveryAndGrouping`.

    Args:
        fields: Optional list of fields to evaluate. If omitted, fields are discovered from
            the current prediction/reference entries.
        format_as_markdown: Whether to format the result as a markdown table. Defaults to True.
        subfield_keys: Optional grouping configuration forwarded to the base collection to
            expand dict-like fields into generated fields such as ``field1.A&B``.
        subfield_values: Optional payload selection for grouped fields, forwarded to the base
            collection.
        sort_fields: Whether to sort the fields in the output. Defaults to False.
        **kwargs: Additional keyword arguments forwarded to :class:`F1MicroSingleFieldMetric`, e.g.,
            ``ignore_subfields`` or ``ignore_missing_entries``.

    Raises:
        ValueError: If ``fields`` contains the reserved aggregate names ``ALL`` or ``AVG``.
    """

    def __init__(
        self,
        format_as_markdown: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(metric_class=F1MicroSingleFieldMetric, **kwargs)

        # reserve aggregate result field names used by this metric
        if self.fields is not None and ("ALL" in self.fields or "AVG" in self.fields):
            raise ValueError("Fields cannot contain 'ALL' or 'AVG' as field names.")

        self.format_as_markdown = format_as_markdown

    @property
    def ignore_missing_entries(self) -> bool:
        return self.metric_kwargs.get("ignore_missing_entries", False)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Compute per-field F1 results together with ``AVG`` and ``ALL`` aggregate entries.

        If ``ignore_missing_entries`` is enabled, fields whose underlying metric never observed
        any true positives, false positives, or false negatives are removed before the macro
        average is computed.

        Returns:
            A dictionary mapping field names to score dictionaries, plus ``AVG`` for the macro
            average across fields and ``ALL`` for the global micro average.
        """
        result = super()._compute(*args, **kwargs)
        if self.ignore_missing_entries:
            # remove results from metrics with empty states to get correct AVG values and shorten the result
            result = {
                name: field_result
                for name, field_result in result.items()
                if any(self.metrics[name].state[key] > 0 for key in ("tp", "fp", "fn"))
            }
        # compute mean for precision, recall, f1 over all fields
        scores_list = defaultdict(list)
        for field_result in result.values():
            for key, value in field_result.items():
                scores_list[key].append(value)
        result["AVG"] = {key: sum(values) / len(values) for key, values in scores_list.items()}

        # compute micro average over all instances based on states of all sub-metrics
        state_total = {
            "tp": sum(metric.state["tp"] for metric in self.metrics.values()),
            "fp": sum(metric.state["fp"] for metric in self.metrics.values()),
            "fn": sum(metric.state["fn"] for metric in self.metrics.values()),
        }
        result["ALL"] = F1MicroSingleFieldMetric.calculate_scores(state=state_total)
        return result

    def _format_result(self, result: dict[str, Any]) -> str:
        """Formats the result as a markdown table if specified, otherwise as pretty-printed JSON.

        Args:
            result: The result dictionary to format.
        Returns: A string representation of the result.
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
