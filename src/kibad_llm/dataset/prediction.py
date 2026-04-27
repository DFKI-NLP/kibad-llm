"""Utilities for loading prediction output files with optional Hydra run metadata.

:func:`load_with_metadata` is the primary entry point used by the evaluate pipeline.
It accepts either:

- ``log=<path>`` – a Hydra run output directory; the function reads
  ``job_return_value.json`` and ``.hydra/overrides.yaml`` to recover the prediction
  file path and run metadata, then wraps the dataset in :class:`DictWithMetadata`.
- ``file=<path>`` – a direct path to a predictions JSONL file (backward-compatible).

The returned dict maps record IDs to dicts with ``prediction`` and ``reference`` keys
(after merging with references via :func:`~kibad_llm.dataset.utils.merge_references_into_predictions`).
:class:`DictWithMetadata` is a thin ``dict`` subclass that carries the Hydra overrides
and job return value as metadata, which the evaluate pipeline can attach to metric results.
"""

import json
import logging
import os

import yaml

from kibad_llm.dataset.json import read_and_preprocess

logger = logging.getLogger(__name__)


class DictWithMetadata(dict):

    def __init__(self, *args, metadata: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self._metadata = metadata

    @property
    def metadata(self) -> dict:
        return self._metadata


def load_with_metadata(
    log: str | None = None,
    file: str | None = None,
    skip_by_id: list[str] | None = None,
    **load_kwargs,
) -> dict:
    """Load a dataset from a prediction log directory, extracting metadata such as Hydra overrides
    and attach it to the dataset. If `log` is not provided, load directly from `file` (backward compatibility).

    Args:
        log: Path to the prediction log directory.
        file: Path to the dataset file.
        skip_by_id: Optional list of IDs to drop respective entries from the dataset after loading.
        **load_kwargs: Additional keyword arguments to pass to `read_and_preprocess`.
    Returns:
        The loaded dataset, possibly wrapped in `DictWithMetadata` if loaded from a log directory.
    """

    metadata = None

    if log is not None:
        if file is not None:
            raise ValueError("Specify either 'log' or 'file', not both.")

        # get job return value from json file
        job_return_value_file = os.path.join(log, "job_return_value.json")
        with open(job_return_value_file) as f:
            job_return_value = json.load(f)

        # get overrides from hydra overrides yaml file
        overrides_file = os.path.join(log, ".hydra", "overrides.yaml")
        with open(overrides_file) as f:
            overrides = yaml.safe_load(f)
        metadata = {"overrides": overrides, "job_return_value": job_return_value}

        # use output file from job return value
        file = job_return_value["output_file"]
    else:
        if file is None:
            raise ValueError("Either 'log' or 'file' must be specified.")

    dataset = read_and_preprocess(file=file, **load_kwargs)
    if skip_by_id is not None:
        skipped = set(skip_by_id) & set(dataset.keys())
        dataset = {k: v for k, v in dataset.items() if k not in skip_by_id}
        logger.warning(f"Skipped {len(skipped)} entries from loaded data: {sorted(skipped)}")
    if metadata is not None:
        dataset = DictWithMetadata(dataset, metadata=metadata)
    return dataset
