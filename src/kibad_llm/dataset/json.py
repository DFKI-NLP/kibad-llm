from collections.abc import Callable
import json
import logging

from datasets import Dataset

logger = logging.getLogger(__name__)


def load_and_preprocess(
    file: str,
    id_key: str,
    process_id: Callable | None = None,
    preprocess: Callable | None = None,
) -> Dataset:
    """Load a dataset from a JSON file and apply optional preprocessing.

    Args:
        file: Path to the JSON or JSON lines file.
        id_key: Key in the JSON objects to use as the unique identifier.
        process_id: Optional function to process IDs.
        preprocess: Optional preprocessing function to apply to the dataset.
    Returns:
        The loaded and preprocessed Dataset.
    """

    process_id = process_id or (lambda x: x)

    logger.info(f"Loading dataset from JSON file: {file} ...")
    dataset = dict()
    with open(file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                line_dict = json.loads(line)
                key = process_id(line_dict[id_key])
                del line_dict[id_key]
                dataset[key] = line_dict

    if preprocess is not None:
        logger.info(f"Apply preprocessing function to dataset: {preprocess} ...")
        dataset = {k: preprocess(v) for k, v in dataset.items()}

    return dataset
