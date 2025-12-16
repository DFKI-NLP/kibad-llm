import json
import os

import yaml

from kibad_llm.dataset.json import read_and_preprocess


class DictWithMetadata(dict):

    def __init__(self, *args, metadata: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self._metadata = metadata

    @property
    def metadata(self) -> dict:
        return self._metadata


def overrides2dict(overrides: list, strip_plus_from_keys: bool = False) -> dict:
    result = {}
    for item in overrides:
        if "=" in item:
            key, value = item.split("=", 1)
            if strip_plus_from_keys:
                key = key.lstrip("+")
            result[key] = value
        else:
            raise ValueError(f"Invalid override format: {item}")
    return result


def load_with_metadata(
    log: str | None = None,
    file: str | None = None,
    strip_plus_from_keys: bool = False,
    **load_kwargs,
) -> dict:
    """Load a dataset from a prediction log directory, extracting metadata such as Hydra overrides
    and attach it to the dataset. If `log` is not provided, load directly from `file` (backward compatibility).

    Args:
        log: Path to the prediction log directory.
        file: Path to the dataset file.
        strip_plus_from_keys: Whether to strip leading '+' from override keys.
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
        overrides_dict = overrides2dict(overrides, strip_plus_from_keys=strip_plus_from_keys)
        metadata = {"overrides": overrides_dict}

        # use output file from job return value
        file = job_return_value["output_file"]
    else:
        if file is None:
            raise ValueError("Either 'log' or 'file' must be specified.")

    dataset = read_and_preprocess(file=file, **load_kwargs)
    if metadata is not None:
        dataset = DictWithMetadata(dataset, metadata=metadata)
    return dataset
