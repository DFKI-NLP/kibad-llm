"""Provides the [`Metric`][.Metric] base class, which defines the interface of metrics.

Classes:
    Metric: Base class, defining the interface of metrics.

"""

from collections.abc import Hashable
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class Metric:
    """Simple base class / interface definition for metrics.

    Methods:
        reset: To reset all internal states. Must be implemented by the subclass.
        update: Calls the private _update method, which must be implemented by the subclass. Used to update internal states with new data.
        compute: Calls the private _compute method, which must be implemented by the subclass. Used to compute and return the metric results.
        show_result: Utility method to print the metric result in a readable format.
    """

    def reset(self) -> None:
        """Reset all internal states.

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Update internal states with new data.

        Args:
            prediction: Predictions made in a dataset.
            reference: Gold data to compare the predictions to.
            record_id: Id to tag the comparison with.

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Calls the private _update method to update internal states with new data.

        Args:
            prediction: Predictions made in a dataset.
            reference: Gold data to compare the predictions to.
            record_id: Id to tag the comparison with.
        """
        self._update(prediction=prediction, reference=reference, record_id=record_id)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Compute and return the metric results.

        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def compute(self, *args, reset: bool = True, **kwargs) -> dict[str, Any]:
        """Wrapper for `_compute`.

        Args:
            *args (Any): Positional args forwarded to the `_compute` implementation.

        Keyword Args:
            reset (bool): If `True`, uses [`reset`][..reset] to reset the internal state after computing the result.
            **kwargs (Any): Keyword args forwarded to the `_compute` implementation.

        Returns:
            result of the evaluation.
        """
        result = self._compute(*args, **kwargs)
        if reset:
            self.reset()
        return result

    def _format_result(self, result: dict[str, Any]) -> str:
        """Utility method to format the metric result as a pretty-printed JSON string.

        Args:
            result: Dict that must be json-serialiseable.

        Returns:
            Input dict as pretty-printed JSON string.
        """
        return json.dumps(result, indent=2)

    def show_result(self, result: dict[str, Any] | None = None, reset: bool = True) -> None:
        """Utility method to print the metric result in a readable format.

        Args:
            result: Dict to pretty-print as JSON string or None to compute the result with [`compute`][..compute]
            reset: Whether to reset after using [`compute`][..compute] to obtain result, if the result arg was None.
        """
        if result is None:
            result = self.compute(reset=reset)

        logger.info(f"Evaluation results:\n{self._format_result(result)}")
