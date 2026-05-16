"""Concrete metric implementations for the evaluation pipeline.

Re-exports the four metric classes used via Hydra configuration:

- [`F1MicroSingleFieldMetric`][kibad_llm.metrics.f1.F1MicroSingleFieldMetric] – micro-averaged F1 for a
  single schema field.
- [`F1MicroMultipleFieldsMetric`][kibad_llm.metrics.f1.F1MicroMultipleFieldsMetric] – F1 across all schema
  fields at once, plus macro average (AVG) and global micro average (ALL).
- [`ConfusionMatrix`][kibad_llm.metrics.confusion_matrix.ConfusionMatrix] – per-label confusion
  matrix (with ``UNDETECTED`` / ``UNASSIGNABLE`` sentinels for FN / FP).
- [`ErrorCollector`][kibad_llm.metrics.statistics.ErrorCollector] – counts extraction errors
  reported in prediction dicts.
- [`MetricCollection`][kibad_llm.metrics.collection.MetricCollection] – fan-out wrapper that
  dispatches ``update`` / ``compute`` to a dict of named sub-metrics.
"""

from .collection import MetricCollection
from .confusion_matrix import ConfusionMatrix
from .f1 import F1MicroMultipleFieldsMetric, F1MicroSingleFieldMetric
from .statistics import ErrorCollector
