"""JSON and JSONL dataset loading with optional compression and preprocessing.

:func:`read_and_preprocess` is the core loader used throughout the dataset package.
It reads plain JSON (as a single object) or JSON Lines (one dict per line, keyed by
``id_key``) from files that may be compressed (gz, bz2, xz, zip, tar, zst) by
delegating decompression to :func:`~kibad_llm.dataset.compression.open_text`.

An optional ``preprocess`` callable is applied to each entry after loading, and
``process_id`` allows transforming the ID key value before it is used as the dict key.
"""

from collections.abc import Callable, Hashable
import json
import logging
from pathlib import Path

from kibad_llm.dataset.compression import open_text

logger = logging.getLogger(__name__)


def read_and_preprocess(
    file: str | Path,
    id_key: str | None = None,
    encoding: str = "utf-8",
    process_id: Callable | None = None,
    preprocess: Callable | None = None,
    archive_member: str | None = None,
    **kwargs,
) -> dict[Hashable, dict]:
    """Read a dataset from a JSON (lines) file (optionally compressed) and preprocess it.

    If `id_key` is provided, the JSON file is assumed to be in JSON lines format,
    and the value corresponding to `id_key` is used as the unique identifier for
    each entry. If `id_key` is None, the entire JSON file is loaded as a single object.

    Compression inference follows pandas' documented behavior ('.gz', '.bz2', '.zip', '.xz',
    '.zst', and tar variants like '.tar.gz').

    Args:
        file: Path to the JSON or JSON lines file.
        id_key: Key in the JSON objects to use as the unique identifier.
        encoding: File encoding to use when reading the file.
        process_id: Optional function to process IDs.
        preprocess: Optional preprocessing function to apply to the dataset.
        archive_member: If the file is an archive, the member to extract (required for tar/zip
            with multiple files).
        **kwargs: Additional keyword arguments to pass to `json.load` or `json.loads`.
    Returns:
        The loaded and preprocessed Dataset.
    """

    process_id = process_id or (lambda x: x)

    logger.info(f"Loading dataset from JSON file: {file} ...")

    with open_text(
        file,
        encoding=encoding,
        archive_member=archive_member,
    ) as f:
        if id_key is None:
            dataset = json.load(f, **kwargs)
        else:
            dataset = {}
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
