from typing import Any

from kibad_llm.metric import Metric


class F1LabelMetric(Metric):
    """Computes precision, recall, and F1 score for single- and multi-label classification tasks.
    Args:
        field: The optional field name in the predictions and references to evaluate.
    """

    def __init__(self, field: str | None = None) -> None:
        self.field = field
        self.reset()

    def reset(self) -> None:
        """Resets all values of the internal state to zero"""
        self.state: dict[str, int] = {"tp": 0, "fp": 0, "fn": 0}

    def _update(self, prediction: Any, reference: Any) -> None:
        """Updates the internal state with the given prediction(s) and reference(s).

        If self.field is set, this method assumes the input to be a dictionary.
        In that case it uses self.field to try and extract the relevant prediction and reference
        values from the prediction and reference dictionaries.
        If self.field is none, this method assumes the inputs to be a list, set, or single value.
        The inputs are later converted into sets.
        Warning:
        !This can obfuscate issues, like an llm returning the same value as prediction 100 times!

        Args:
            prediction: Dict of predicted value(s) or predicted values directly
            prediction: Dict of reference value(s) or reference values directly, to compare to
        """
        if self.field:
            prediction = prediction.get(self.field, [])
            reference = reference.get(self.field, [])

        if prediction is None:
            prediction = []
        elif (
            not isinstance(prediction, list)
            and not isinstance(prediction, tuple)
            and not isinstance(prediction, set)
        ):
            prediction = [prediction]
        if reference is None:
            reference = []
        elif (
            not isinstance(reference, list)
            and not isinstance(reference, tuple)
            and not isinstance(reference, set)
        ):
            reference = [reference]

        self.state["tp"] += len(set(prediction) & set(reference))
        self.state["fp"] += len(set(prediction) - set(reference))
        self.state["fn"] += len(set(reference) - set(prediction))

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


class F1MultiLabelMetric(F1LabelMetric):
    """Computes precision, recall, and F1 score for multi-label classification tasks.
    Args:
        field: The optional field name in the predictions and references to evaluate.
    """


class F1SingleLabelMetric(F1LabelMetric):
    """Computes precision, recall, and F1 score for single-label classification tasks.
    Args:
        field: The field name in the predictions and references to evaluate.
    """
