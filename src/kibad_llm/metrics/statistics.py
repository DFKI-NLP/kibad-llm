from collections import defaultdict
from collections.abc import Hashable
import logging
from typing import Any

from kibad_llm.metric import Metric

logger = logging.getLogger(__name__)


class ErrorCollector(Metric):
    """Collects error messages from model predictions and provides statistics on their occurrences.

    Args:
        show_errors (bool): If True, logs each collected error message.
        type_separator (str): Separator used to split error messages into type and details.
    """

    def __init__(self, show_errors: bool = False, type_separator: str = ": ") -> None:
        self.show_errors = show_errors
        self.type_separator = type_separator
        self.reset()

    def reset(self) -> None:
        self.state: list[str] = []

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        errors_with_none = []
        if "error" in prediction:
            errors_with_none.append(prediction["error"])
        elif "error_list" in prediction and isinstance(prediction["error_list"], list):
            errors_with_none.extend(prediction["error_list"])

        # separate None values
        errors_none = ["no_error" for e in errors_with_none if e is None]
        errors = [e for e in errors_with_none if e is not None]
        if self.show_errors:
            for error in errors:
                logger.info(f"Collected error (id={record_id}): {error}")
        self.state.extend(errors)
        self.state.extend(errors_none)

    def _compute(self) -> dict[str, Any]:

        # group errors by message type and count occurrences
        errors_grouped = defaultdict(list)
        for error in self.state:
            err_parts = error.split(self.type_separator, 1)
            errors_grouped[err_parts[0]].append(error)

        # just return counts for now
        counts = {k: len(v) for k, v in errors_grouped.items()}
        return counts
