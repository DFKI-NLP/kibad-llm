from typing import Any


class Metric:
    """Simple base class / interface definition for metrics."""

    def reset(self) -> None:
        """Reset all internal states."""
        raise NotImplementedError("Subclasses should implement this method.")

    def _update(self, *args, **kwargs) -> None:
        """Update internal states with new data."""
        raise NotImplementedError("Subclasses should implement this method.")

    def update(self, *args, **kwargs) -> None:
        self._update(*args, **kwargs)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Compute and return the metric results."""
        raise NotImplementedError("Subclasses should implement this method.")

    def compute(self, *args, reset: bool = True, **kwargs) -> dict[str, Any]:
        result = self._compute(*args, **kwargs)
        if reset:
            self.reset()
        return result
