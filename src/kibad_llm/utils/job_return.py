import json
from pathlib import Path

from kibad_llm.utils.dictionary import flatten_dict_s


def load_subdirs(
    parent_dir: Path,
    filename="job_return_value.json",
    strip_id_keys: bool = True,
    flatten: bool = False,
    exclude_keys: list[str] | None = None,
) -> list[dict]:
    """Load job return value json files from subdirectories of the given parent directory.

    Args:
        parent_dir: Path to the parent directory containing subdirectories with return value files.
        filename: Name of the file to load from each subdirectory.
        strip_id_keys: Whether to strip the top-level identifier keys from loaded multi-run results.
        flatten: Whether to flatten nested dictionaries in the loaded data.
        exclude_keys: List of keys to exclude from the loaded data. Applied after flattening if enabled.
    Returns:
        A list of dictionaries containing the loaded data from each subdirectory.
    """

    # get sub directories, 1 level only
    # (so we do not load the individual job returns if called on a multi-run directories)
    run_dirs = [p for p in Path(parent_dir).iterdir() if p.is_dir()]

    # assume that each subdir contains a 'job_return_value.json' from a multi-run evaluation
    data = [json.loads((subdir / filename).read_text()) for subdir in run_dirs]

    # keep the keys / identifiers? If loading multi-run results, the data may have the form
    # [{'id1': {...}, {'id2': {...}}, ...], i.e. each individual dict is wrapped in an id key.
    has_id_keys = all(isinstance(d, dict) for d in data)
    if has_id_keys and strip_id_keys:
        data = [subdict for d in data for subdict in d.values()]

    if flatten:
        data = [flatten_dict_s(d, sep=".") for d in data]

    if exclude_keys is not None:
        for d in data:
            for key in exclude_keys:
                if key in d:
                    del d[key]
    return data
