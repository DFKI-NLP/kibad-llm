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

    The number of compatible partial alignments is:

        sum_k binom(m, k) * binom(n, k) * k!

    where `k = 0` corresponds to the alignment in which no gold-only item is paired
    with a prediction-only item. In the confusion-matrix computation below, this count
    is used only as an accounting device for distributing ambiguous error mass.
    """
    return sum(comb(m, k) * comb(n, k) * factorial(k) for k in range(min(m, n) + 1))


class ConfusionMatrix(MetricWithTpFpFnEntries):
    """Build an alignment-averaged confusion matrix from tp/fp/fn entry state.

    In multi-label settings, unmatched gold and predicted labels do not define a unique
    off-diagonal confusion matrix. For example, if one record contains a missed gold
    label `A` and an extra predicted label `B`, the tp/fp/fn state alone does not tell
    us whether this should be accounted for as `A -> B`, as `A -> UNDETECTED` plus
    `UNASSIGNABLE -> B`, or as part of another possible alignment.

    This metric therefore uses an alignment-averaged accounting rule per record:

    - exact true-positive labels are counted deterministically on the diagonal;
    - unmatched gold and predicted labels are distributed over all compatible partial
      one-to-one alignments between false negatives and false positives;
    - all compatible partial alignments are weighted equally;
    - unmatched gold labels that are not aligned to a prediction contribute to
      `undetected_label`;
    - unmatched predicted labels that are not aligned to a gold label contribute to
      `unassignable_label`.

    The resulting off-diagonal entries are expected ambiguous error mass under this
    uniform partial-alignment assumption. They are useful for exploratory error analysis,
    but they are not directly observed misclassification counts and do not provide
    statistical significance or uncertainty estimates.

    Warning:
        Because the metric operates on sets, duplicate predicted or gold labels are
        collapsed in multi-label settings per record.

    Warning:
        Off-diagonal entries indicate possible label-shift mass under the accounting
        rule, not evidence that a particular label shift actually occurred.
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
            unassignable_label: Label used on the gold axis for predicted labels that
                remain unaligned to any gold label.
            undetected_label: Label used on the prediction axis for gold labels that
                remain unaligned to any prediction.

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
        """Convert tp/fp/fn entry state into alignment-averaged cell counts.

        For each record, true positives are counted deterministically on the diagonal.
        False negatives and false positives are ambiguous because the tp/fp/fn state
        does not contain an observed alignment between missed gold labels and extra
        predicted labels.

        Let `m = len(fn)`, `n = len(fp)`, and `T(m, n)` be the number of compatible
        partial one-to-one alignments between the false negatives and false positives.
        Under the uniform partial-alignment accounting rule, the expected contributions
        are:

        - `gold_i -> pred_j`: `T(m - 1, n - 1) / T(m, n)`
        - `gold_i -> undetected_label`: `T(m - 1, n) / T(m, n)`
        - `unassignable_label -> pred_j`: `T(m, n - 1) / T(m, n)`

        These values should be interpreted as expected ambiguous error mass, not as
        observed misclassification probabilities. If either side is empty, the accounting
        is deterministic: false negatives are fully counted as undetected, and false
        positives are fully counted as unassignable.

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

        # Compute the confusion-matrix contribution independently per record/document.
        for state in self.state_per_record.values():
            tp = list(state["tp"])
            fn = list(state["fn"])
            fp = list(state["fp"])

            # Exact matches are observed and unambiguous, so they go to the diagonal.
            for label in tp:
                counts[(str(label), str(label))] += 1.0

            m = len(fn)
            n = len(fp)

            # No missed gold labels: all extra predictions remain unaligned to gold.
            if m == 0:
                for pred_label in fp:
                    counts[(self.unassignable_label, str(pred_label))] += 1.0
                continue

            # No extra predictions: all missed gold labels remain unaligned to predictions.
            if n == 0:
                for gold_label in fn:
                    counts[(str(gold_label), self.undetected_label)] += 1.0
                continue

            # Otherwise, the relation between false negatives and false positives is
            # latent. We distribute mass uniformly over all compatible partial
            # one-to-one alignments instead of choosing one arbitrary alignment.
            total = num_partial_matchings(m, n)

            # Expected mass for a specific possible label shift gold_i -> pred_j.
            # This is not an observed confusion probability, only the marginal mass
            # induced by the uniform partial-alignment accounting rule.
            p_shift = num_partial_matchings(m - 1, n - 1) / total

            # Expected mass for a specific false-negative gold label remaining unaligned.
            p_undetected = num_partial_matchings(m - 1, n) / total

            # Expected mass for a specific false-positive predicted label remaining unaligned.
            p_unassignable = num_partial_matchings(m, n - 1) / total

            for gold_label in fn:
                # Distribute expected ambiguous mass over all possible label shifts from
                # this missed gold label to each extra predicted label.
                for pred_label in fp:
                    counts[(str(gold_label), str(pred_label))] += p_shift

                # Add the expected mass for this gold label remaining undetected.
                counts[(str(gold_label), self.undetected_label)] += p_undetected

            # Add the expected mass for each prediction remaining unassignable.
            for pred_label in fp:
                counts[(self.unassignable_label, str(pred_label))] += p_unassignable

        return counts

    def _compute(self) -> dict[str, dict[str, float]]:
        """Compute the alignment-averaged confusion matrix.

        Returns:
            A nested dictionary mapping gold labels to predicted-label expected counts.
            Counts may be fractional because ambiguous false-positive/false-negative
            cases are distributed over compatible partial one-to-one alignments.

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

            # At this point, pandas uses predicted labels as rows and gold labels as
            # columns because `res` is structured as gold -> predicted -> count.
            gold_labels = res_df.columns
            pred_labels = res_df.index

            # Sort labels alphabetically, but keep placeholder labels at the end to make
            # the markdown table easier to read.
            gold_labels_sorted = sorted(
                [gold_label for gold_label in gold_labels if gold_label != self.unassignable_label]
            )
            if self.unassignable_label in gold_labels:
                gold_labels_sorted = gold_labels_sorted + [self.unassignable_label]

            pred_labels_sorted = sorted(
                [pred_label for pred_label in pred_labels if pred_label != self.undetected_label]
            )
            if self.undetected_label in pred_labels:
                pred_labels_sorted = pred_labels_sorted + [self.undetected_label]

            res_df_sorted = res_df.loc[pred_labels_sorted, gold_labels_sorted]

            # Transpose for display so rows are gold labels and columns are predictions,
            # which is the conventional confusion-matrix orientation used by `_compute`.
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
