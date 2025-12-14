from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def warn_once(msg: str) -> None:
    """Log a warning message only once by caching the function call."""
    logger.warning(f"{msg} (this message will only be shown once)")
