"""Confusion-matrix metric built on shared tp/fp/fn state."""

from collections import defaultdict
from collections.abc import Hashable
import logging
from typing import Any

import pandas as pd

from kibad_llm.metrics.base import MetricWithTpFpFnEntries

logger = logging.getLogger(__name__)


class ConfusionMatrix(MetricWithTpFpFnEntries):
    """Build a confusion matrix from inherited tp/fp/fn entry state.

    Predictions that have no matching gold label are counted under ``unassignable_label``.
    Gold labels with no matching prediction are counted under ``undetected_label``.

    WARNING:
    !Since the metric operates on sets, this can obfuscate if the LLM produces duplicate labels
    !in multi-label settings.

    Args:
        unassignable_label: Label used on the gold side to encode spurious predicted labels
            (false positives). Defaults to "UNASSIGNABLE".
        undetected_label: Label used on the prediction side to encode missed gold labels
            (false negatives). Defaults to "UNDETECTED".
        show_as_markdown: If True, logs the confusion matrix as markdown on the console when
            calling compute().
        **kwargs: Additional keyword arguments for entry-to-set preparation and tp/fp/fn
            collection. See `MetricWithTpFpFnEntries` for supported options.
    """

    def __init__(
        self,
        show_as_markdown: bool = False,
        unassignable_label: str = "UNASSIGNABLE",
        undetected_label: str = "UNDETECTED",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.unassignable_label = unassignable_label
        self.undetected_label = undetected_label
        self.show_as_markdown = show_as_markdown

    def _build_counts(
        self, state: dict[str, set[tuple[Hashable, Any]]]
    ) -> dict[tuple[str, str], int]:
        """Convert shared tp/fp/fn state into confusion-matrix cell counts."""
        counts: dict[tuple[str, str], int] = defaultdict(int)

        if any(label == self.unassignable_label for _, label in state["tp"] | state["fn"]):
            raise ValueError(
                f"The gold reference has the label '{self.unassignable_label}' for unassignable instances. "
                f"Set a different unassignable_label."
            )
        if any(label == self.undetected_label for _, label in state["tp"] | state["fp"]):
            raise ValueError(
                f"The prediction has the label '{self.undetected_label}' for undetected instances. "
                f"Set a different undetected_label."
            )

        for _, label in state["tp"]:
            counts[(str(label), str(label))] += 1
        for _, label in state["fn"]:
            counts[(str(label), self.undetected_label)] += 1
        for _, label in state["fp"]:
            counts[(self.unassignable_label, str(label))] += 1

        return counts

    def _compute(self) -> dict[str, dict[str, int]]:
        counts = self._build_counts(self.state)

        res: dict[str, dict[str, int]] = {}
        for gold_label, pred_label in sorted(counts):
            res.setdefault(gold_label, {})[pred_label] = counts[(gold_label, pred_label)]

        if self.show_as_markdown:
            res_df = pd.DataFrame(res).fillna(0)
            # index is prediction, columns is gold
            gold_labels = res_df.columns
            pred_labels = res_df.index

            # re-arrange index and columns: sort and put reserved labels at the end
            gold_labels_sorted = sorted(
                [gold_label for gold_label in gold_labels if gold_label != self.unassignable_label]
            )
            # re-add unassignable_label at the end, if it was in the gold labels
            if self.unassignable_label in gold_labels:
                gold_labels_sorted = gold_labels_sorted + [self.unassignable_label]
            pred_labels_sorted = sorted(
                [pred_label for pred_label in pred_labels if pred_label != self.undetected_label]
            )
            # re-add undetected_label at the end, if it was in the pred labels
            if self.undetected_label in pred_labels:
                pred_labels_sorted = pred_labels_sorted + [self.undetected_label]
            res_df_sorted = res_df.loc[pred_labels_sorted, gold_labels_sorted]

            # transpose and show as markdown: index is now gold, columns is prediction
            msg = "Confusion Matrix"
            if self.field is not None:
                msg += f" for field '{self.field}'"
            logger.info(f"{msg}:\n{res_df_sorted.T.to_markdown()}")
        return res
