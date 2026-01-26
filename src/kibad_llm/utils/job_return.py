from collections.abc import Callable, Iterable
import json
import logging
import math
from pathlib import Path
import re
import traceback
from typing import Any

import numpy as np
import pandas as pd

from kibad_llm.utils.dictionary import flatten_dict_s

logger = logging.getLogger(__name__)


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

    print("pandas", pd.__version__, "numpy", np.__version__)
    print("len(data)", len(data))
    print("index type", type(data.index), "index dtype", getattr(data.index, "dtype", None))
    print("group key dtype", data[by[0]].dtype, "NA in key", data[by[0]].isna().sum())

    dtypes = data[cols_agg_numeric].dtypes
    print("numeric dtypes value_counts:\n", dtypes.value_counts())
    print(
        "nullable columns:",
        [c for c in cols_agg_numeric if str(data[c].dtype) in ("Float64", "Int64", "boolean")][
            :20
        ],
    )

    g = data.groupby(by=by)
    for c in cols_agg_numeric:
        try:
            _ = g[c].mean()
        except Exception as e:
            print("FAILS on column:", c, "dtype:", data[c].dtype)
            raise

    dfs_concat = []
    # group by the specified columns ...
    result_grouped = data.groupby(by=list(by))
    if len(cols_agg_numeric) > 0:
        try:
            # ... and calculate the mean and std for numeric columns (and flatten the column MultiIndex)
            result_numeric = result_grouped[cols_agg_numeric].agg(numeric_agg_func)
        except Exception as e:
            print("Error during aggregation:", e)
            print("cols_agg_numeric:", cols_agg_numeric)
            print("all columns:", data.columns.tolist())
            print("by:", by)
            print("numeric_agg_func:", numeric_agg_func)
            # show full stack trace
            e_with_traceback = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            print(e_with_traceback)
            raise e

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
