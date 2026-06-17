"""Confusion-matrix metrics built on shared tp/fp/fn state.

Classes:
    ConfusionMatrix: Build a confusion matrix from the shared tp/fp/fn entry state for one field.
    ConfusionMatrixCollection: Build confusion matrices for multiple fields with optional field
        discovery and grouped-field expansion.
"""

from collections import defaultdict
from functools import cache
import logging
from math import comb, factorial
from typing import Any

import pandas as pd

from kibad_llm.metrics.base import MetricWithTpFpFnEntries
from kibad_llm.metrics.collection import MetricCollectionWithFieldDiscoveryAndGrouping

logger = logging.getLogger(__name__)


@cache
def num_partial_matchings(m: int, n: int) -> int:
    """Return the number of partial one-to-one alignments between two item sets.

    A partial alignment links `k` of `m` gold-only items to `k` of `n` prediction-only
    items, for any `k` from 0 to `min(m, n)`. The selected items are matched
    bijectively.

    The number of such alignments is:

        sum_k binom(m, k) * binom(n, k) * k!

    where `k = 0` corresponds to the alignment in which no gold-only item is paired
    with a prediction-only item.
    """
    return sum(comb(m, k) * comb(n, k) * factorial(k) for k in range(min(m, n) + 1))


class ConfusionMatrix(MetricWithTpFpFnEntries):
    """Build an expected confusion matrix from inherited tp/fp/fn entry state.

    Exact true-positive labels are counted on the diagonal. For unmatched labels in
    multi-label records, the metric distinguishes three possible cases:

    - a false-negative gold label may correspond to a false-positive predicted label
      (a label shift);
    - a false-negative gold label may be genuinely undetected;
    - a false-positive predicted label may be genuinely unassignable.

    Since the tp/fp/fn set representation does not identify which false-positive label,
    if any, corresponds to which false-negative label, this metric averages over all
    possible partial one-to-one alignments between false negatives and false positives
    within each record. All such alignments are assumed to be equally likely.

    Consequently, the resulting confusion matrix may contain fractional expected
    counts. The placeholders `undetected_label` and `unassignable_label` are used for
    unmatched gold and prediction labels, respectively.

    Warning:
        Because the metric operates on sets, duplicate predicted or gold labels are
        collapsed in multi-label settings per record.

    Warning:
        The uniform alignment assumption is a neutral modeling choice under missing
        alignment information. It is not evidence that a particular label shift actually
        occurred.
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
            show_as_markdown: Whether `compute()` should log the resulting confusion
                matrix as a markdown table.
            unassignable_label: Label used on the gold axis for prediction labels that
                cannot be assigned to any gold label.
            undetected_label: Label used on the prediction axis for gold labels that
                were not detected by any prediction.

        Keyword Args:
            field: Optional field to extract from dictionary inputs.
            flatten_dicts: Whether nested dictionaries should be flattened before
                comparison.
            ignore_subfields: Optional subfields to ignore when hashing dictionary
                values.
            ignore_missing_entries: Whether one-sided empty entries should be skipped.
        """
        super().__init__(**kwargs)
        self.unassignable_label = unassignable_label
        self.undetected_label = undetected_label
        self.show_as_markdown = show_as_markdown

    def _build_counts(self) -> dict[tuple[str, str], float]:
        """Convert shared tp/fp/fn entry state into expected confusion-matrix counts.

        For each record, true positives are counted deterministically on the diagonal.
        False negatives and false positives are treated as ambiguous: a false-negative
        gold label may either be aligned to one false-positive predicted label or remain
        undetected; similarly, a false-positive predicted label may either be aligned to
        one false-negative gold label or remain unassignable.

        Let `m = len(fn)`, `n = len(fp)`, and `T(m, n)` be the number of partial
        one-to-one alignments between the false negatives and false positives. Under a
        uniform distribution over these alignments, the expected contributions are:

        - `gold_i -> pred_j`: `T(m - 1, n - 1) / T(m, n)`
        - `gold_i -> undetected_label`: `T(m - 1, n) / T(m, n)`
        - `unassignable_label -> pred_j`: `T(m, n - 1) / T(m, n)`

        If either side is empty, the result is deterministic: false negatives are fully
        counted as undetected, and false positives are fully counted as unassignable.

        Returns:
            A mapping from `(gold_label, predicted_label)` cells to expected counts.

        Raises:
            ValueError: If predictions or references already use one of the reserved
                placeholder labels.
        """
        counts: dict[tuple[str, str], float] = defaultdict(float)

        if any(
            label == self.unassignable_label for _, label in self.state["tp"] | self.state["fn"]
        ):
            raise ValueError(
                f"The gold reference has the label '{self.unassignable_label}' for "
                f"unassignable instances. Set a different unassignable_label."
            )
        if any(label == self.undetected_label for _, label in self.state["tp"] | self.state["fp"]):
            raise ValueError(
                f"The prediction has the label '{self.undetected_label}' for "
                f"undetected instances. Set a different undetected_label."
            )

        # Calculate the expected confusion-matrix contribution independently per record.
        for state in self.state_per_record.values():
            tp = list(state["tp"])
            fn = list(state["fn"])
            fp = list(state["fp"])

            # Exact label matches are unambiguous and therefore contribute to the diagonal.
            for label in tp:
                counts[(str(label), str(label))] += 1.0

            m = len(fn)
            n = len(fp)

            # If there are no missed gold labels, all extra predictions are unassignable.
            if m == 0:
                for pred_label in fp:
                    counts[(self.unassignable_label, str(pred_label))] += 1.0
                continue

            # If there are no extra predictions, all missed gold labels are undetected.
            if n == 0:
                for gold_label in fn:
                    counts[(str(gold_label), self.undetected_label)] += 1.0
                continue

            # Otherwise, the relation between false negatives and false positives is
            # ambiguous. We average uniformly over all partial one-to-one alignments.
            total = num_partial_matchings(m, n)

            # Probability that a specific false-negative label is aligned to a specific
            # false-positive label, i.e. interpreted as a label shift.
            p_shift = num_partial_matchings(m - 1, n - 1) / total

            # Probability that a specific false-negative label is not aligned to any
            # false-positive label and is therefore genuinely undetected.
            p_undetected = num_partial_matchings(m - 1, n) / total

            # Probability that a specific false-positive label is not aligned to any
            # false-negative label and is therefore genuinely unassignable.
            p_unassignable = num_partial_matchings(m, n - 1) / total

            for gold_label in fn:
                # Add expected mass for all possible label shifts from this gold label.
                for pred_label in fp:
                    counts[(str(gold_label), str(pred_label))] += p_shift

                # Add expected mass for the case where this gold label was missed.
                counts[(str(gold_label), self.undetected_label)] += p_undetected

            # Add expected mass for predicted labels that are not explained by any
            # false-negative gold label.
            for pred_label in fp:
                counts[(self.unassignable_label, str(pred_label))] += p_unassignable

        return counts

    def _compute(self) -> dict[str, dict[str, float]]:
        """Compute the expected confusion matrix from accumulated tp/fp/fn state.

        Returns:
            A nested dictionary mapping gold labels to predicted-label expected counts.
            Counts may be fractional because ambiguous false-positive/false-negative
            cases are averaged over all possible partial one-to-one alignments.

        Raises:
            ValueError: If predictions or references already use one of the reserved
                placeholder labels.
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
