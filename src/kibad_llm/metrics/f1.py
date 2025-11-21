from collections import defaultdict
from typing import Any

from pandas import DataFrame

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet
from kibad_llm.metrics.collection import MetricCollection


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
        **kwargs: Keyword arguments for entry-to-set preparation. See
            `MetricWithPrepareEntryAsSet` for supported options.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.reset()

    def reset(self) -> None:
        """Resets all values of the internal state to zero"""
        self.state: dict[str, int] = {"tp": 0, "fp": 0, "fn": 0}

    def _update(self, prediction: Any, reference: Any) -> None:
        """Updates the internal state with the given prediction(s) and reference(s).

        Args:
            prediction: Dict of predicted value(s) or predicted values directly
            prediction: Dict of reference value(s) or reference values directly, to compare to
        """
        prediction = self._prepare_entry_as_set(prediction)
        reference = self._prepare_entry_as_set(reference)

        self.state["tp"] += len(prediction & reference)
        self.state["fp"] += len(prediction - reference)
        self.state["fn"] += len(reference - prediction)

    @staticmethod
    def calculate_scores(tp: int, fp: int, fn: int) -> dict[str, float]:
        """Calculates precision, recall and f1 from true positives, false positives and false negatives.

        returns: dictionary with precision, recall and f1
        """

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes the micro average of precision, recall and f1 score."""
        return self.calculate_scores(tp=self.state["tp"], fp=self.state["fp"], fn=self.state["fn"])


class F1MultipleFieldsMetric(MetricCollection):

    def __init__(
        self,
        fields: list[str],
        format_as_markdown: bool = True,
        sort_fields: bool = False,
        **kwargs,
    ) -> None:
        """Computes F1MicroSingleFieldMetric for multiple fields at once.

        Args:
            fields: List of fields to compute F1MicroSingleFieldMetric for.
            format_as_markdown: Whether to format the result as a markdown table. Defaults to True.
            **kwargs: Additional keyword arguments for F1MicroSingleFieldMetric, e.g., ignore_subfields.
        """
        # for now, just raise error if fields contain MICRO or MACRO
        if "MICRO" in fields or "MACRO" in fields:
            raise ValueError("Fields cannot contain 'MICRO' or 'MACRO' as field names.")

        if sort_fields:
            fields = sorted(fields)
        super().__init__(
            metrics={field: F1MicroSingleFieldMetric(field=field, **kwargs) for field in fields}
        )

        self.format_as_markdown = format_as_markdown

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes the results for all sub-metrics and MICRO and MACRO averages.

        Returns:
            A dictionary mapping field names to their computed results.
        """
        result = super()._compute(*args, **kwargs)

        # compute MACRO average from result
        if len(result) > 0:
            # collect all values for each score
            result_lists = defaultdict(list)
            for metric_result in result.values():
                for key, value in metric_result.items():
                    result_lists[key].append(value)
            # compute average for score
            result["MACRO"] = {
                key: sum(values) / len(values) for key, values in result_lists.items()
            }

        # compute MICRO average
        total_tp = sum(metric.state["tp"] for metric in self.metrics.values())
        total_fp = sum(metric.state["fp"] for metric in self.metrics.values())
        total_fn = sum(metric.state["fn"] for metric in self.metrics.values())
        result["MICRO"] = F1MicroSingleFieldMetric.calculate_scores(
            tp=total_tp, fp=total_fp, fn=total_fn
        )
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
