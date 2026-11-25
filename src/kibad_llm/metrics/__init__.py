"""Public metric implementations and metric-related helpers.

Modules:
    collection: Helpers for grouping multiple metric instances.
    confusion_matrix: Confusion-matrix metric based on tp/fp/fn entry tracking for single- and multi-field.
    f1: Single-field and multi-field micro-F1 metrics.
    errors: Error-collection metrics.
    tpfpfn: Raw tp/fp/fn entry collector for single- and multi-field.
    snippet_judge: LLM-judge metric comparing evidence snippets with gold entries.

Classes:
    MetricCollection: Aggregate multiple sub-metrics.
    ConfusionMatrix: Build confusion matrices from tp/fp/fn entry state for one field.
    ConfusionMatrixCollection: Build confusion matrices from tp/fp/fn entry state for multiple fields at once.
    F1MicroSingleFieldMetric: Compute micro-F1 for one field.
    F1MicroMultipleFieldsMetric: Compute micro-F1 for multiple fields plus aggregates.
    ErrorCollector: Collect and count prediction errors.
    TpFpFnCollector: Return raw tp/fp/fn entries for inspection.
    TpFpFnCollectorCollection: Return raw tp/fp/fn entries for multiple fields at once.
    SnippetJudgeMetric: Judge evidence snippets against gold entries with an LLM.
"""

from .collection import MetricCollection
from .confusion_matrix import ConfusionMatrix, ConfusionMatrixCollection
from .errors import ErrorCollector
from .f1 import F1MicroMultipleFieldsMetric, F1MicroSingleFieldMetric
from .snippet_judge import SnippetJudgeMetric
from .tpfpfn import TpFpFnCollector, TpFpFnCollectorCollection

__all__ = [
    "MetricCollection",
    "ConfusionMatrix",
    "ConfusionMatrixCollection",
    "F1MicroMultipleFieldsMetric",
    "F1MicroSingleFieldMetric",
    "ErrorCollector",
    "TpFpFnCollector",
    "TpFpFnCollectorCollection",
    "SnippetJudgeMetric",
]
