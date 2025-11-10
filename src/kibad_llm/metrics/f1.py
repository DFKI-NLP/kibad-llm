from typing import Any

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet


class MicroF1Metric(MetricWithPrepareEntryAsSet):
    """Computes precision, recall, and F1 score for single- and multi-label classification tasks.

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

        # we want to acknowledge empty predictions and references as true positives TODO: really?? or true negatives?
        if len(prediction) == len(reference) == 0:
            self.state["tp"] += 1
            return

        self.state["tp"] += len(prediction & reference)
        self.state["fp"] += len(prediction - reference)
        self.state["fn"] += len(reference - prediction)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes the micro average of precision, recall and f1

        returns: dictionary with precision, recall and f1
        """
        precision = (
            self.state["tp"] / (self.state["tp"] + self.state["fp"])
            if (self.state["tp"] + self.state["fp"]) > 0
            else 0.0
        )
        recall = (
            self.state["tp"] / (self.state["tp"] + self.state["fn"])
            if (self.state["tp"] + self.state["fn"]) > 0
            else 0.0
        )
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
