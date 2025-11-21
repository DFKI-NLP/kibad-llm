from typing import Any

from kibad_llm.metric import Metric


class MetricCollection(Metric):
    """A metric that aggregates multiple sub-metrics.

    Args:
        metrics: A dictionary mapping metric names to Metric instances.
    """

    def __init__(self, metrics: dict[str, Metric]) -> None:
        super().__init__()
        self.metrics = metrics

    def reset(self) -> None:
        """Resets all sub-metrics."""
        for metric in self.metrics.values():
            metric.reset()

    def _update(self, *args, **kwargs) -> None:
        """Updates all sub-metrics with the given data.

        Args:
            *args: Positional arguments to pass to each sub-metric's update method.
            **kwargs: Keyword arguments to pass to each sub-metric's update method.
        """
        for metric in self.metrics.values():
            metric.update(*args, **kwargs)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes and returns the results of all sub-metrics.

        Returns:
            A dictionary mapping metric names to their computed results.
        """
        results = {}
        for name, metric in self.metrics.items():
            results[name] = metric.compute(*args, reset=False, **kwargs)
        return results
