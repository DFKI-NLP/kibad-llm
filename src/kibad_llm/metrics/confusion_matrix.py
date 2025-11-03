from collections import defaultdict
import logging
from typing import Any

import pandas as pd

from kibad_llm.metric import Metric

logger = logging.getLogger(__name__)


class ConfusionMatrix(Metric):
    """Computes a confusion matrix for single- and multi-label classification tasks.

    Args:
        field: Optional field key as str. If self.field is set, it is used as key for
            prediction and reference, which need to be dicts then.
        unassignable_label: The label to use for false negative annotations. Defaults to "UNASSIGNABLE".
        undetected_label: The label to use for false positive annotations. Defaults to "UNDETECTED".
        show_as_markdown: If True, logs the confusion matrix as markdown on the console when calling compute().
    """

    def __init__(
        self,
        field: str | None = None,
        show_as_markdown: bool = False,
        unassignable_label: str = "UNASSIGNABLE",
        undetected_label: str = "UNDETECTED",
    ):
        super().__init__()
        self.field = field
        self.unassignable_label = unassignable_label
        self.undetected_label = undetected_label
        self.show_as_markdown = show_as_markdown
        self.reset()

    def reset(self) -> None:
        self.counts: dict[tuple[str, str], int] = defaultdict(int)

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

    def calculate_counts(
        self,
        prediction: set,
        reference: set,
    ) -> dict[tuple[str, str], int]:

        if self.unassignable_label in reference:
            raise ValueError(
                f"The gold reference has the label '{self.unassignable_label}' for unassignable instances. "
                f"Set a different unassignable_label."
            )
        if self.undetected_label in prediction:
            raise ValueError(
                f"The prediction has the label '{self.undetected_label}' for undetected instances. "
                f"Set a different undetected_label."
            )

        # (gold_label, pred_label) -> count
        counts: dict[tuple[str, str], int] = defaultdict(int)
        # True positives: labels in both reference and prediction
        for label in reference & prediction:
            counts[(label, label)] += 1

        # False negatives: labels in reference but not in prediction
        for label in reference - prediction:
            counts[(label, self.unassignable_label)] += 1

        # False positives: labels in prediction but not in reference
        for label in prediction - reference:
            counts[(self.undetected_label, label)] += 1

        return counts

    def add_counts(self, counts: dict[tuple[str, str], int]) -> None:
        for key, value in counts.items():
            self.counts[key] += value

    def _update(self, prediction: Any, reference: Any) -> None:
        pred_set = self._prepare_entry(prediction)
        ref_set = self._prepare_entry(reference)
        new_counts = self.calculate_counts(prediction=pred_set, reference=ref_set)
        self.add_counts(new_counts)

    def _compute(self) -> dict[str, dict[str, int]]:

        res: dict[str, dict[str, int]] = defaultdict(dict)
        for gold_label, pred_label in sorted(self.counts):
            res[gold_label][pred_label] = self.counts[(gold_label, pred_label)]

        if self.show_as_markdown:
            res_df = pd.DataFrame(res).fillna(0)
            # index is prediction, columns is gold
            gold_labels = res_df.columns
            pred_labels = res_df.index

            # re-arrange index and columns: sort and put undetected_label and unassignable_label at the end
            gold_labels_sorted = sorted(
                [gold_label for gold_label in gold_labels if gold_label != self.undetected_label]
            )
            # re-add undetected_label at the end, if it was in the gold labels
            if self.undetected_label in gold_labels:
                gold_labels_sorted = gold_labels_sorted + [self.undetected_label]
            pred_labels_sorted = sorted(
                [pred_label for pred_label in pred_labels if pred_label != self.unassignable_label]
            )
            # re-add unassignable_label at the end, if it was in the pred labels
            if self.unassignable_label in pred_labels:
                pred_labels_sorted = pred_labels_sorted + [self.unassignable_label]
            res_df_sorted = res_df.loc[pred_labels_sorted, gold_labels_sorted]

            # transpose and show as markdown: index is now gold, columns is prediction
            msg = "Confusion Matrix"
            if self.field is not None:
                msg += f" for field '{self.field}'"
            logger.info(f"{msg}:\n{res_df_sorted.T.to_markdown()}")
        return res
