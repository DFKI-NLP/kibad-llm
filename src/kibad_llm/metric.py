from typing import Any


class Metric:

    def reset(self) -> None:
        raise NotImplementedError("Subclasses should implement this method.")

    def _update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Subclasses should implement this method.")

    def update(self, *args, **kwargs) -> None:
        self._update(*args, **kwargs)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        raise NotImplementedError("Subclasses should implement this method.")

    def compute(self, *args, reset: bool = True, **kwargs) -> dict[str, Any]:
        result = self._compute(*args, **kwargs)
        if reset:
            self.reset()
        return result
