from collections.abc import Hashable
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class Metric:
    """Simple base class / interface definition for metrics."""

    def reset(self) -> None:
        """Reset all internal states."""
        raise NotImplementedError("Subclasses should implement this method.")

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Update internal states with new data."""
        raise NotImplementedError("Subclasses should implement this method.")

    def update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        self._update(prediction=prediction, reference=reference, record_id=record_id)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Compute and return the metric results."""
        raise NotImplementedError("Subclasses should implement this method.")

    def compute(self, *args, reset: bool = True, **kwargs) -> dict[str, Any]:
        result = self._compute(*args, **kwargs)
        if reset:
            self.reset()
        return result

    def _format_result(self, result: dict[str, Any]) -> str:
        """Utility method to format the metric result as a pretty-printed JSON string."""
        return json.dumps(result, indent=2)

    def show_result(self, result: dict[str, Any] | None = None, reset: bool = True) -> None:
        """Utility method to print the metric result in a readable format."""
        if result is None:
            result = self.compute(reset=reset)

        logger.info(f"Evaluation results:\n{self._format_result(result)}")
