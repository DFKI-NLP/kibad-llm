from collections.abc import Callable, Hashable
import json
import logging

logger = logging.getLogger(__name__)


def read_and_preprocess(
    file: str,
    id_key: str | None = None,
    encoding: str = "utf-8",
    process_id: Callable | None = None,
    preprocess: Callable | None = None,
    **kwargs,
) -> dict[Hashable, dict]:
    """Read a dataset from a JSON (lines) file and apply optional preprocessing.
    If `id_key` is provided, the JSON file is assumed to be in JSON lines format,
    and the value corresponding to `id_key` is used as the unique identifier for
    each entry. If `id_key` is None, the entire JSON file is loaded as a single object.

    Args:
        file: Path to the JSON or JSON lines file.
        id_key: Key in the JSON objects to use as the unique identifier.
        encoding: File encoding to use when reading the file.
        process_id: Optional function to process IDs.
        preprocess: Optional preprocessing function to apply to the dataset.
        **kwargs: Additional keyword arguments to pass to `json.load` or `json.loads`.
    Returns:
        The loaded and preprocessed Dataset.
    """

    process_id = process_id or (lambda x: x)

    logger.info(f"Loading dataset from JSON file: {file} ...")
    if id_key is None:
        with open(file, encoding=encoding) as f:
            dataset = json.load(f, **kwargs)
    else:
        dataset = dict()
        with open(file, encoding=encoding) as f:
            for line in f:
                if line.strip():
                    line_dict = json.loads(line, **kwargs)
                    key = process_id(line_dict[id_key])
                    del line_dict[id_key]
                    dataset[key] = line_dict

    if preprocess is not None:
        logger.info(f"Apply preprocessing function to dataset: {preprocess} ...")
        dataset = {k: preprocess(v) for k, v in dataset.items()}

    return dataset
