from typing import Any

from kibad_llm.metric import Metric


class F1SingleLabelMetric(Metric):
    """Computes precision, recall, and F1 score for single-label classification tasks.
    Args:
        field: The field name in the predictions and references to evaluate.
    """

    def __init__(self, field: str) -> None:
        self.field = field
        self.reset()

    def reset(self) -> None:
        self.state: dict[str, int] = {"tp": 0, "fp": 0, "fn": 0}

    def _update(self, predictions: dict[str, Any], references: dict[str, Any]) -> None:
        pred = predictions.get(self.field, None)
        ref = references.get(self.field, None)
        if pred == ref and pred is not None:
            self.state["tp"] += 1
        else:
            if pred is not None:
                self.state["fp"] += 1
            if ref is not None:
                self.state["fn"] += 1

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
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
