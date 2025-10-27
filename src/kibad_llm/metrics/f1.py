from typing import Any

from kibad_llm.metric import Metric


class MicroF1Metric(Metric):
    """Computes precision, recall, and F1 score for single- and multi-label classification tasks.

        If self.field is set, this class assumes the prediction and reference inputs to be dictionaries.
        In that case it uses self.field to try and extract the relevant prediction and reference
        values from the prediction and reference dictionaries.
        If self.field is none, this class assumes the inputs to be a list, set, or single value.
        The inputs are later converted into sets by self._prepare_entry.
        Warning:
        !This can obfuscate issues, like an llm returning the same value as prediction 100 times!

    Args:
        field: The optional field name in the predictions and references to evaluate.
    """

    def __init__(self, field: str | None = None) -> None:
        self.field = field
        self.reset()

    def reset(self) -> None:
        """Resets all values of the internal state to zero"""
        self.state: dict[str, int] = {"tp": 0, "fp": 0, "fn": 0}

    def _prepare_entry(self, entry: Any) -> set:
        """Helper method to convert any prediction or reference value into a set of values.

        Uses self.field to retrieve the correct values from a given dict if necessary.
        Returns empty set when there is no value.
        Wraps any found values into a set whilst keeping the unique values unaltered

        Args:
            entry: Any kind of data structure to maybe extract from and eventually wrap in a set.
        Returns: A set of whatever relevant value was put in.
        """
        if self.field is not None:
            entry = entry.get(self.field, None)
        if entry is None:
            return set()
        if isinstance(entry, (list, set)):
            return set(entry)
        return {entry}

    def _update(self, prediction: Any, reference: Any) -> None:
        """Updates the internal state with the given prediction(s) and reference(s).

        Args:
            prediction: Dict of predicted value(s) or predicted values directly
            prediction: Dict of reference value(s) or reference values directly, to compare to
        """
        prediction = self._prepare_entry(prediction)
        reference = self._prepare_entry(reference)

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
