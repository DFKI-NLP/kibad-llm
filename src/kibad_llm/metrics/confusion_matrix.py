"""Confusion-matrix metrics built on shared tp/fp/fn state.

Classes:
    ConfusionMatrix: Build a confusion matrix from the shared tp/fp/fn entry state for one field.
    ConfusionMatrixCollection: Build confusion matrices for multiple fields with optional field
        discovery and grouped-field expansion.
"""

from collections import defaultdict
from collections.abc import Hashable
import logging
from typing import Any

import pandas as pd

from kibad_llm.metrics.base import MetricWithTpFpFnEntries
from kibad_llm.metrics.collection import MetricCollectionWithFieldDiscoveryAndGrouping

logger = logging.getLogger(__name__)


class ConfusionMatrix(MetricWithTpFpFnEntries):
    """Build a confusion matrix from inherited tp/fp/fn entry state for one field.

    Predictions that have no matching gold label are counted under `unassignable_label`.
    Gold labels with no matching prediction are counted under `undetected_label`.

    Warning:
        Because the metric operates on sets, duplicate predicted labels are collapsed in
        multi-label settings (per record).
    """

    def __init__(
        self,
        show_as_markdown: bool = False,
        unassignable_label: str = "UNASSIGNABLE",
        undetected_label: str = "UNDETECTED",
        **kwargs: Any,
    ):
        """Initialize the confusion-matrix metric.

        Args:
            show_as_markdown: Whether `compute()` should log the resulting confusion matrix as a
                markdown table.
            unassignable_label: Label used on the gold axis for false positives.
            undetected_label: Label used on the prediction axis for false negatives.

        Keyword Args:
            field: Optional field to extract from dictionary inputs.
            flatten_dicts: Whether nested dictionaries should be flattened before comparison.
            ignore_subfields: Optional subfields to ignore when hashing dictionary values.
            ignore_missing_entries: Whether one-sided empty entries should be skipped.
        """
        super().__init__(**kwargs)
        self.unassignable_label = unassignable_label
        self.undetected_label = undetected_label
        self.show_as_markdown = show_as_markdown

    def _build_counts(self) -> dict[tuple[str, str], float]:
        """Convert shared tp/fp/fn entry state into confusion-matrix cell counts.

        Args:
            state: Mapping of `tp`, `fp`, and `fn` to tracked `(record_id, label)` pairs.

        Returns:
            A mapping from `(gold_label, predicted_label)` cells to their counts.

        Raises:
            ValueError: If predictions or references already use one of the reserved placeholder
                labels.
        """
        counts: dict[tuple[str, str], float] = defaultdict(float)

        if any(
            label == self.unassignable_label for _, label in self.state["tp"] | self.state["fn"]
        ):
            raise ValueError(
                f"The gold reference has the label '{self.unassignable_label}' for unassignable instances. "
                f"Set a different unassignable_label."
            )
        if any(label == self.undetected_label for _, label in self.state["tp"] | self.state["fp"]):
            raise ValueError(
                f"The prediction has the label '{self.undetected_label}' for undetected instances. "
                f"Set a different undetected_label."
            )

        # calculate for each document independently
        for state in self.state_per_record.values():
            for label in state["tp"]:
                counts[(str(label), str(label))] += 1
            for label in state["fn"]:
                # each false negative could be either one of the false positives ("shift")
                # or undetected ("real false negative")
                other_labels = list(state["fp"]) + [self.undetected_label]
                for other_label in other_labels:
                    counts[(str(label), str(other_label))] += 1 / len(other_labels)
            for label in state["fp"]:
                # each false positive could be either one of the false negatives ("shift")
                # or unassignable ("real false positive")
                other_labels = list(state["tp"]) + [self.unassignable_label]
                for other_label in other_labels:
                    counts[(str(other_label), str(label))] += 1 / len(other_labels)

        return counts

    def _compute(self) -> dict[str, dict[str, float]]:
        """Compute the confusion matrix from the accumulated tp/fp/fn entry state.

        Returns:
            A nested dictionary mapping gold labels to prediction-label counts.

        Raises:
            ValueError: If predictions or references already use one of the reserved placeholder
                labels.
        """
        counts = self._build_counts()

        res: dict[str, dict[str, float]] = {}
        for gold_label, pred_label in sorted(counts):
            res.setdefault(gold_label, {})[pred_label] = counts[(gold_label, pred_label)]

        if self.show_as_markdown:
            res_df = pd.DataFrame(res).fillna(0.0)
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


class ConfusionMatrixCollection(MetricCollectionWithFieldDiscoveryAndGrouping[ConfusionMatrix]):
    """Build confusion matrices for multiple fields at once.

    The collection lazily creates one `ConfusionMatrix` per field and inherits optional dynamic
    field discovery plus grouped-field expansion from
    `MetricCollectionWithFieldDiscoveryAndGrouping`. Nested dict-like fields can therefore be
    expanded into generated field names such as `organism_trends.Amphibien&Wald` before each
    per-field confusion matrix is updated.

    Attributes:
        fields: Explicit field names to evaluate, or `None` to discover them dynamically.
        subfield_keys: Optional rules for expanding nested dict-like fields into generated fields.
        subfield_values: Optional rules restricting which nested values are compared after
            expansion.
        metric_kwargs: Keyword arguments forwarded to the per-field `ConfusionMatrix` instances.
    """

    def __init__(
        self,
        **kwargs,
    ) -> None:
        """Initialize a multi-field confusion-matrix collection.

        Keyword Args:
            fields: Optional allowlist of fields to evaluate. If omitted, fields are discovered
                from the union of keys present in each prediction/reference pair.
            subfield_keys: Optional mapping describing how nested entries are split into generated
                fields.
            subfield_values: Optional mapping restricting which nested values are kept after field
                expansion.
            sort_fields: Whether to sort the fields in the output. Defaults to False.
            show_as_markdown: Whether each per-field confusion matrix should be logged as a markdown
                table when computed.
            unassignable_label: Label used on the gold axis for false positives.
            undetected_label: Label used on the prediction axis for false negatives.
            flatten_dicts: Whether nested dictionaries should be flattened before comparison.
            ignore_subfields: Optional subfields to ignore when hashing dictionary payloads.
            ignore_missing_entries: Whether one-sided empty entries should be skipped.
        """
        super().__init__(metric_class=ConfusionMatrix, **kwargs)
