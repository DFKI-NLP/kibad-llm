from collections.abc import Callable
import logging

from datasets import Dataset

logger = logging.getLogger(__name__)


def load_and_preprocess(
    file: str,
    drop_columns: list[str] | None = None,
    preprocess: Callable | None = None,
) -> Dataset:
    """Load a dataset from a JSON file and apply optional preprocessing.

    Args:
        file: Path to the JSON or JSON lines file.
        drop_columns: Optional list of column names to drop from the dataset.
        preprocess: Optional preprocessing function to apply to the dataset.
    Returns:
        The loaded and preprocessed Dataset.
    """

    logger.info(f"Loading dataset from JSON file: {file} ...")
    dataset = Dataset.from_json(file)

    # this needs to happen before any mapping is applied (which may fail otherwise)
    if drop_columns:
        logger.info(f"Dropping columns: {drop_columns} ...")
        columns_remove = [col for col in drop_columns if col in dataset.column_names]
        columns_not_found = set(drop_columns) - set(columns_remove)
        if len(columns_not_found) > 0:
            logger.warning(
                f"Columns not found in dataset, but specified to drop: {columns_not_found}"
            )
        dataset = dataset.remove_columns(columns_remove)

    if preprocess is not None:
        logger.info(f"Apply preprocessing function to dataset: {preprocess} ...")
        dataset = dataset.map(preprocess)

    return dataset
