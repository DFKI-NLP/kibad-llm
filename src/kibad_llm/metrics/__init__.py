"""Public metric implementations and metric-related helpers.

Modules:
    collection: Helpers for grouping multiple metric instances.
    confusion_matrix: Confusion-matrix metric based on tp/fp/fn entry tracking.
    f1: Single-field and multi-field micro-F1 metrics.
    errors: Error-collection metrics.
    tpfpfn: Raw tp/fp/fn entry collector.

Classes:
    MetricCollection: Aggregate multiple sub-metrics.
    ConfusionMatrix: Build confusion matrices from tp/fp/fn entry state for one field.
    F1MicroSingleFieldMetric: Compute micro-F1 for one field.
    F1MicroMultipleFieldsMetric: Compute micro-F1 for multiple fields plus aggregates.
    ErrorCollector: Collect and count prediction errors.
    TpFpFnCollector: Return raw tp/fp/fn entries for inspection.
"""

from .collection import MetricCollection
from .confusion_matrix import ConfusionMatrix
from .errors import ErrorCollector
from .f1 import F1MicroMultipleFieldsMetric, F1MicroSingleFieldMetric
from .tpfpfn import TpFpFnCollector

__all__ = [
    "MetricCollection",
    "ConfusionMatrix",
    "F1MicroMultipleFieldsMetric",
    "F1MicroSingleFieldMetric",
    "ErrorCollector",
    "TpFpFnCollector",
]
