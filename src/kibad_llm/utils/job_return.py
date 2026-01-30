from collections.abc import Callable, Hashable, Iterable
import json
import logging
import math
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
import yaml

from kibad_llm.utils.dictionary import flatten_dict_s
from kibad_llm.utils.path import get_directories_with_file

logger = logging.getLogger(__name__)


def overrides_to_dict(
    overrides: Iterable[str], remove_plus_prefix: bool = False
) -> dict[str, str]:
    """Convert a list of overrides to a dictionary.

    Example:
        >>> overrides = ["a=1", "b=2", "+c=3"]
        >>> overrides_to_dict(overrides, remove_plus_prefix=True)
        {'a': '1', 'b': '2', 'c': '3'}
    Args:
        overrides (list[str]): The list of overrides.
        remove_plus_prefix (bool, optional): If True, remove the '+' prefix from keys. Defaults to False.
    Returns:
        dict[str, str]: The dictionary of overrides.
    """
    override_dict = {}
    for override in overrides:
        key, value = override.split("=", 1)
        if remove_plus_prefix:
            key = key.lstrip("+")
        override_dict[key] = value
    return override_dict


def dict_to_overrides(d: dict[Hashable, Any], remove_na: bool = False) -> list[str]:
    """Convert a dictionary to a overrides.
    Example:
        >>> dict_to_overrides({"a": 1, "b": 2})
        ['a=1', 'b=2']
        >>> dict_to_overrides({"a": 1, "b": None}, remove_na=True)
        ['a=1']
        >>> dict_to_overrides({"+c": 3, "d": float('nan')}, remove_na=True)
        ['+c=3']
    """
    overrides = []
    for key, value in d.items():
        if remove_na and (value is None or (isinstance(value, float) and math.isnan(value))):
            continue
        overrides.append(f"{key}={value}")
    return overrides


def load(
    directory: Path,
    subdir_pattern: str | list[str] = "",
    filename="job_return_value.json",
    strip_id_keys: bool = True,
    flatten: bool = False,
    exclude_keys: list[str] | None = None,
) -> list[dict]:
    """Load job return value json file(s) from the given directory.

    Args:
        directory: Path to the directory containing return value file(s).
        subdir_pattern: One or multiple pattern to match subdirectories (e.g., "*/" to load from
            all immediate subdirs).
        filename: Name of the file to load from each subdirectory.
        strip_id_keys: Whether to strip the top-level identifier keys from loaded multi-run results.
        flatten: Whether to flatten nested dictionaries in the loaded data.
        exclude_keys: List of keys to exclude from the loaded data. Applied after flattening if enabled.
    Returns:
        A list of dictionaries containing the loaded data from each subdirectory.
    """
    if isinstance(subdir_pattern, str):
        subdir_pattern = [subdir_pattern]
    file_paths = []
    for s_pattern in subdir_pattern:
        if s_pattern.strip() != "" and not s_pattern.endswith("/"):
            raise ValueError(f"subdir_pattern must end with '/', got: {s_pattern}")
        current_file_paths = list(directory.glob(s_pattern + filename))
        logger.info(
            f"Loading data from files (subdir_pattern+filename: {s_pattern + filename}):\n%s",
            "\n".join(map(str, current_file_paths)),
        )
        file_paths.extend(current_file_paths)

    # read all json files
    data = [json.loads(file_path.read_text()) for file_path in file_paths]

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


def load_run(
    directory: Path, filename: str = "job_return_value.json", load_overrides: bool = True
) -> dict:
    """Load a job return value json file from the given directory.

    Args:
        directory: Path to the directory containing the return value file.
        filename: Name of the file to load.
        load_overrides: Whether to load overrides from '.hydra/overrides.yaml' if it exists and
    Returns:
        A dictionary containing the loaded data.
    """
    file_path = directory / filename
    logger.info(f"Loading job return value from file: {file_path}")
    data = json.loads(file_path.read_text())

    if load_overrides:
        overrides_path = directory / ".hydra" / "overrides.yaml"
        if overrides_path.exists():
            if "overrides" in data:
                logger.warning(
                    f"Overrides already exist in job return value data, but will be overwritten: "
                    f"{data['overrides']}"
                )
            overrides = yaml.safe_load(overrides_path.read_text())
            data["overrides"] = overrides_to_dict(overrides, remove_plus_prefix=True)

    return data


def load_runs(
    directory: Path,
    subdir: str | list[str] = "",
    filename: str = "job_return_value.json",
    load_overrides: bool = True,
    flatten: bool = False,
    exclude_keys: list[str] | None = None,
) -> list[dict]:
    """Load job return value json file(s) from subdirectories of the given directory. Only the
    leaf subdirectories containing the specified filename are considered (i.e. multi-run
    results are excluded).

    Args:
        directory: Path to the directory containing return value file(s).
        subdir: One or multiple subdirectory names under `directory` to search in.
        filename: Name of the file to load from each subdirectory.
        load_overrides: Whether to load overrides from '.hydra/overrides.yaml' if it exists.
        flatten: Whether to flatten nested dictionaries in the loaded data.
        exclude_keys: List of keys to exclude from the loaded data. Applied after flattening if enabled.
    """

    if isinstance(subdir, str):
        subdir = [subdir]

    dir_paths = get_directories_with_file(
        paths=[str(directory / sub_dir) for sub_dir in subdir],
        filename=filename,
        leafs_only=True,
    )
    logger.info(
        f"Loading {filename} from {len(dir_paths)} directories (directory: {directory}, subdir: {subdir}):\n%s",
        "\n".join(map(str, dir_paths)),
    )

    # read all json files
    data = [
        load_run(directory=Path(dir_path), filename=filename, load_overrides=load_overrides)
        for dir_path in dir_paths
    ]

    if flatten:
        data = [flatten_dict_s(d, sep=".") for d in data]

    if exclude_keys is not None:
        for d in data:
            for key in exclude_keys:
                if key in d:
                    del d[key]
    return data


def _filter_nan_and_join(values: Iterable, sep: str) -> str:
    return sep.join([v for v in values if not isinstance(v, float) or not math.isnan(v)])


def multi_index_to_single(index: pd.Index, sep: str = ".") -> pd.Index:
    """Convert a MultiIndex to a single Index by joining the levels with a separator and
    removing NaN values.

    Example:
        >>> index = pd.MultiIndex.from_tuples([('a', 'b'), ('c', np.nan)])
        >>> multi_index_to_single(index)
        Index(['a.b', 'c'], dtype='object')

    Args:
        index (pd.MultiIndex): The MultiIndex to convert.
        sep (str, optional): The separator to use between the levels. Defaults to ".".

    Returns:
        pd.Index: The converted Index.
    """
    if not isinstance(index, pd.MultiIndex):
        return index

    return index.map(lambda values: _filter_nan_and_join(values, sep))


def mixed_group_by(
    data: pd.DataFrame,
    by: list[str] | str,
    numeric_agg_func: str | Callable | list[str | Callable] = "mean",
    numeric_fill_na: Any | None = None,
    force_list_col_regex: str | None = None,
    columns_name: str | None = None,
) -> pd.DataFrame:
    """
    Group a DataFrame by one or more columns and aggregate numeric vs. non-numeric
    columns differently.

    This helper is meant for "mixed" tables where you want summary statistics for
    numeric columns (e.g., mean/std/min/max) while keeping all values for
    non-numeric columns as lists.

    Behavior
    --------
    - ``by`` is normalized to a list of column names.
    - Dtypes are tightened via ``DataFrame.convert_dtypes()`` (helps separate
      numeric vs. non-numeric columns reliably).
    - Missing values in grouping columns are filled with the empty string ``""``
      so rows with NA keys still participate in grouping.
    - Numeric columns (``np.number``) are aggregated with ``numeric_agg_func``.
      If multiple functions are used, the resulting MultiIndex columns are
      flattened via ``multi_index_to_single(..., sep=".")``.
    - All remaining columns are aggregated using ``list`` (one list per group).
    - Columns that are entirely NA after aggregation are dropped.

    Parameters
    ----------
    data:
        Input DataFrame to group and aggregate.
    by:
        Column name or list of column names to group by.
    numeric_agg_func:
        Aggregation function(s) for numeric columns, passed to
        ``DataFrameGroupBy.agg``. Can be a pandas agg string (e.g. ``"mean"``),
        a callable, or a list mixing both (e.g. ``["mean", "std"]``).
    numeric_fill_na:
        If not ``None``, fill NA values in the aggregated numeric result with
        this value (applied after aggregation).
    force_list_col_regex:
        Optional regex. Columns whose names match this pattern are treated as
        non-numeric (i.e., aggregated as ``list``) even if their dtype is numeric.
        Useful for numeric-coded identifiers that should not be summarized.
    columns_name:
        Optional name for the resulting DataFrame columns.

    Returns
    -------
    pd.DataFrame
        Aggregated DataFrame with:
        - one row per group,
        - flattened numeric aggregation columns (e.g., ``"score.mean"``),
        - list-aggregated non-numeric columns,
        - and no all-NA columns.
    """

    # make a copy to not modify the original data
    data = data.copy()

    if isinstance(by, str):
        by = [by]

    # fix dtypes: convert object dtypes to more specific dtypes
    data = data.convert_dtypes()

    additional_cols_not_numeric = []
    if force_list_col_regex is not None:
        pattern = re.compile(force_list_col_regex)
        additional_cols_not_numeric = [col for col in data.columns if pattern.match(col)]

    cols_agg_numeric = [
        col
        for col in data.select_dtypes(include=[np.number]).columns
        if col not in additional_cols_not_numeric
    ]
    cols_agg_list = [col for col in data.columns if col not in cols_agg_numeric]

    for col in by:
        # replace na values in col with "" to not miss groupings
        data[col] = data[col].fillna("")
        # remove the group_by columns from numeric and non-numeric columns
        if col in cols_agg_numeric:
            cols_agg_numeric.remove(col)
        if col in cols_agg_list:
            cols_agg_list.remove(col)

    dfs_concat = []
    # group by the specified columns ...
    result_grouped = data.groupby(by=list(by))
    if len(cols_agg_numeric) > 0:
        # ... and calculate the mean and std for numeric columns (and flatten the column MultiIndex)
        result_numeric = result_grouped[cols_agg_numeric].agg(numeric_agg_func)
        result_numeric.columns = multi_index_to_single(result_numeric.columns, sep=".")

        if numeric_fill_na is not None:
            result_numeric = result_numeric.fillna(numeric_fill_na)

        dfs_concat.append(result_numeric)

    if len(cols_agg_list) > 0:
        # ... and for non-numeric columns, return lists of values
        result_other = result_grouped[cols_agg_list].agg(list)

        dfs_concat.append(result_other)

    if len(dfs_concat) == 0:
        # nothing to aggregate, return empty dataframe with correct index
        return pd.DataFrame(index=result_grouped.size().index)

    # combine both results
    result = pd.concat(dfs_concat, axis=1)

    # drop columns that are completely NaN (otherwise to_markdown fails)
    result = result.dropna(axis=1, how="all")

    if columns_name:
        result.columns.name = columns_name

    return result
