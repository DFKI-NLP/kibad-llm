from collections.abc import Callable, Iterable
import json
import math
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

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


def group_by(
    data: pd.DataFrame,
    by: list[str] | str,
    numeric_agg_func: str | Callable | list[str | Callable] = "mean",
    numeric_fill_na: Any | None = None,
    force_list_col_regex: str | None = None,
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

    # group by the specified columns ...
    result_grouped = data.groupby(by=list(by))
    # ... and calculate the mean and std for numeric columns (and flatten the column MultiIndex)
    result_numeric = result_grouped[cols_agg_numeric].agg(numeric_agg_func)
    result_numeric.columns = multi_index_to_single(result_numeric.columns, sep=".")

    if numeric_fill_na is not None:
        result_numeric = result_numeric.fillna(numeric_fill_na)

    # ... and for non-numeric columns, return lists of values
    result_other = result_grouped[cols_agg_list].agg(list)
    # combine both results
    result = pd.concat([result_numeric, result_other], axis=1)
    # drop columns that are completely NaN (otherwise to_markdown fails)
    result = result.dropna(axis=1, how="all")

    return result
