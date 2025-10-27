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

    def _update(self, prediction: dict[str, Any], reference: dict[str, Any]) -> None:
        pred = prediction.get(self.field, None)
        ref = reference.get(self.field, None)
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


class F1MultiLabelMetric(Metric):
    """Computes precision, recall, and F1 score for single-label classification tasks.
    Args:
        field: The field name in the predictions and references to evaluate.
    """

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields
        self.reset()

    def reset(self) -> None:
        self.states: dict[str, F1SingleLabelMetric] = {
            field: F1SingleLabelMetric(field) for field in self.fields
        }

    def _update(self, predictions: dict[str, Any], references: dict[str, Any]) -> None:
        for field in self.fields:
            self.states[field].update(predictions, references)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        global_tp = 0
        global_fp = 0
        global_fn = 0
        global_metric: dict[str, Any] = {}
        sum_precision = 0
        sum_recall = 0

        # compute metrics for individual fields
        for field, state in self.states.items():
            current_state = state.compute()
            global_metric[field] = current_state
            sum_precision += current_state["precision"]
            sum_recall += current_state["recall"]

            global_tp += state.state["tp"]
            global_fp += state.state["fp"]
            global_fn += state.state["fn"]

        # compute micro average metrics
        micro_avg_precision = (
            global_tp / (global_tp + global_fp) if (global_tp + global_fp) > 0 else 0.0
        )
        micro_avg_recall = (
            global_tp / (global_tp + global_fn) if (global_tp + global_fn) > 0 else 0.0
        )
        micro_avg_f1 = (
            2 * (micro_avg_precision * micro_avg_recall) / (micro_avg_precision + micro_avg_recall)
            if (micro_avg_precision + micro_avg_recall) > 0
            else 0.0
        )

        global_metric["micro_avg_precision"] = micro_avg_precision
        global_metric["micro_avg_recall"] = micro_avg_recall
        global_metric["micro_avg_f1"] = micro_avg_f1

        # compute macro average metrics
        macro_avg_precision = sum_precision / len(self.states)
        macro_avg_recall = sum_recall / len(self.states)
        macro_avg_f1 = (
            2 * (macro_avg_precision * macro_avg_recall) / (macro_avg_precision + macro_avg_recall)
            if (macro_avg_precision + macro_avg_recall) > 0
            else 0.0
        )

        global_metric["macro_avg_precision"] = macro_avg_precision
        global_metric["macro_avg_recall"] = macro_avg_recall
        global_metric["macro_avg_f1"] = macro_avg_f1

        return global_metric
