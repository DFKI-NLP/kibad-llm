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
        self.state: list[list[str]] = []

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        errors: list[list[str]] = []
        found_error_keys = []
        if "error" in prediction:
            if prediction["error"] is not None:
                errors.append([prediction["error"]])
            else:
                errors.append([])
            found_error_keys.append("error")
        if "error_list" in prediction and isinstance(prediction["error_list"], list):
            for e in prediction["error_list"]:
                if e is not None:
                    errors.append([e])
                else:
                    errors.append([])
            found_error_keys.append("error_list")
        if "errors" in prediction:
            errors.append(prediction["errors"])
            found_error_keys.append("errors")
        if "errors_list" in prediction and isinstance(prediction["errors_list"], list):
            errors.extend(prediction["errors_list"])
            found_error_keys.append("errors_list")

        if len(found_error_keys) == 0:
            raise ValueError(
                f"No error keys found in prediction for record id={record_id}. "
                f"Expected one of: 'error', 'error_list', 'errors', 'errors_list'."
            )
        if len(found_error_keys) > 1:
            raise ValueError(
                f"Multiple error keys found in prediction for record id={record_id}: "
                f"{found_error_keys}. Please provide only one of these keys."
            )

        if self.show_errors:
            for error in errors:
                logger.info(f"Collected error (id={record_id}): {error}")
        self.state.extend(errors)

    def _compute(self) -> dict[str, Any]:

        # group errors by message type and count occurrences
        errors_grouped = defaultdict(list)
        for errors in self.state:
            # overall no error / with error
            if len(errors) == 0:
                errors_grouped["no_error"].append("")
            else:
                errors_grouped["with_error"].append("")
            # detailed error types
            for error in errors:
                err_parts = error.split(self.type_separator, 1)
                errors_grouped[err_parts[0]].append(error)

        # just return counts for now
        counts = {k: len(v) for k, v in errors_grouped.items()}
        return counts
