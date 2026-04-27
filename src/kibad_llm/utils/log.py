"""Logging helpers.

Provides :func:`warn_once`, which emits a :mod:`logging` warning for a given message
only the first time it is called (subsequent calls with the same message are silently
ignored via ``lru_cache``).  Useful for warning about deprecated arguments or
suboptimal configuration choices inside hot-path code without flooding the logs.
"""

from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def warn_once(msg: str) -> None:
    """Log a warning message only once by caching the function call."""
    logger.warning(f"{msg} (this message will only be shown once)")
