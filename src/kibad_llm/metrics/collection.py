from collections.abc import Hashable, Mapping
from typing import Any, Generic, TypeVar

from kibad_llm.metric import Metric

T = TypeVar("T", bound=Metric)


class MetricCollection(Metric, Generic[T]):
    """A metric that aggregates multiple sub-metrics.

    Args:
        metrics: A dictionary mapping metric names to Metric instances.
    """

    def __init__(self, metrics: dict[str, T] | None = None, sort_fields: bool = False) -> None:
        super().__init__()
        self.metrics: dict[str, T] = metrics or dict()
        self.sort_fields = sort_fields

    def add_metric(self, name: str, metric: T) -> None:
        """Adds a new metric to the collection."""
        if name in self.metrics:
            raise ValueError(f"Metric {name} already exists")
        self.metrics[name] = metric

    def reset(self) -> None:
        """Resets all sub-metrics."""
        for metric in self.metrics.values():
            metric.reset()

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Updates all sub-metrics with the given data."""
        for metric in self.metrics.values():
            metric.update(prediction=prediction, reference=reference, record_id=record_id)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes and returns the results of all sub-metrics.

        Returns:
            A dictionary mapping metric names to their computed results.
        """
        results = {}
        names = list(self.metrics.keys())
        if self.sort_fields:
            names = sorted(names)
        for name in names:
            results[name] = self.metrics[name].compute(*args, reset=False, **kwargs)
        return results
