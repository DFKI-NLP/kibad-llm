import argparse
import json
import logging
import math

import pandas as pd

from kibad_llm.utils.dictionary import flatten_dict_simple

logger = logging.getLogger(__name__)


def _get_list_cols(df: pd.DataFrame) -> list[str]:
    """Get names of columns in a dataframe where all non-null entries are lists.

    Args:
        df: input dataframe
    Returns:
        list of column names where all non-null entries are lists
    Raises:
        ValueError: if any column has mixed list and non-list entries
    """
    cols_with_entries = df.columns[df.notnull().any()].tolist()
    # columns where at least one value is a list
    cols_with_any_list = [
        c for c in cols_with_entries if df[c].apply(lambda x: isinstance(x, list)).any()
    ]

    # columns where every non-null value is a list
    cols_all_lists = [
        c for c in cols_with_entries if df[c].dropna().apply(lambda x: isinstance(x, list)).all()
    ]

    cols_mixed = set(cols_with_any_list) - set(cols_all_lists)
    if len(cols_mixed) > 0:
        raise ValueError(f"Columns with mixed list and non-list entries found: {cols_mixed}")

    return cols_all_lists


def _sort_with_none(l: list, remove_none: bool = False) -> list:
    """Sort a list, placing None and NaN values at the end."""

    def is_nan(x):
        try:
            return math.isnan(x)  # works for float and numpy.float*
        except (TypeError, ValueError):
            return False

    core = [x for x in l if x is not None and not is_nan(x)]
    tail = [x for x in l if x is None or is_nan(x)]
    result = sorted(core)
    if not remove_none:
        result += tail
    return result


def get_unique_single_and_multi_values(
    df: pd.DataFrame,
) -> tuple[dict[str, list], dict[str, list]]:
    """
    Get unique values for single-label and multi-label columns in a dataframe.

    Args:
        df: input dataframe
    Returns:
        A tuple of two dictionaries:
        - a dict mapping single-label column names to their unique values
        - a dict mapping multi-label column names to their unique values
    """

    none_cols = [c for c in df.columns if df[c].isnull().all()]
    if len(none_cols) > 0:
        logger.warning(f"Columns with all None values found:\n{none_cols}")
    multi_label_cols = _get_list_cols(df)
    logger.info(f"Found {len(multi_label_cols)} multi-label columns:\n{multi_label_cols}")
    # assume all other columns are single-label
    single_label_cols = [c for c in df.columns if c not in none_cols + multi_label_cols]
    logger.info(f"Found {len(single_label_cols)} single-label columns:\n{single_label_cols}")

    unique_values_single = {
        col: _sort_with_none(df[col].unique().tolist()) for col in single_label_cols
    }
    # remove None values from multi-label unique entries
    unique_values_multi = {
        col: _sort_with_none(df[col].explode().unique().tolist(), remove_none=True)
        for col in multi_label_cols
    }

    return unique_values_single, unique_values_multi


def show_unique_values_summary(input_file: str, top_n: int = 20, key_sep: str = ".") -> None:
    """
    Show a summary of unique values in a JSONL file with nested entries.
    """

    df = pd.read_json(input_file, lines=True)
    df_flat = df.apply(
        lambda row: pd.Series(flatten_dict_simple(d=row.to_dict(), sep=key_sep)), axis="columns"
    )

    # get unique entries
    unique_values_single, unique_values_multi = get_unique_single_and_multi_values(df=df_flat)
    # combine both dicts
    unique_dict = {**unique_values_single, **unique_values_multi}

    # show numbers on console
    unique_dict_len = {dict_name: len(dict_list) for dict_name, dict_list in unique_dict.items()}
    logger.info(
        f"number of unique entries per key:\n{json.dumps(unique_dict_len, indent=2, sort_keys=True)}\n"
    )

    unique_dict_less_k = {
        k: unique_dict[k] for k in sorted(unique_dict) if len(unique_dict[k]) < top_n
    }
    # sort entries for better readability
    unique_dict_less_k_sorted = dict(
        sorted(unique_dict_less_k.items(), key=lambda item: len(item[1]))
    )
    # lines = "\n".join(f'{k}: {v}' for k, v in unique_dict_less_k_sorted.items())
    lines = json.dumps(unique_dict_less_k_sorted, indent=2, sort_keys=True, ensure_ascii=False)
    logger.info(
        f"show unique entries for {len(unique_dict_less_k_sorted)} keys with less "
        f"than {top_n} entries sorted by number of entries (#remaining keys: "
        f"{len(unique_dict_len) - len(unique_dict_less_k_sorted)}):\n{lines}"
    )


if __name__ == "__main__":
    # show info level logs
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Extract unique values from Faktencheck database JSONL file. "
        'Some columns have nested entries, e.g. "direct_driver", these '
        "are a list of a dicts. The script flattens these nested entries such that "
        'the keys are joined with a "." and the list entries are flattened into a single list. '
        "E.g. {'direct_driver': [{'type': 'A'}, {'type': 'B'}]} becomes "
        '{"direct_driver.type": ["A", "B"]}. See `utils.dictionary.flatten_dict_simple` for details.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default="data/interim/faktencheck-db/faktencheck-db-converted_2025-08-19.jsonl",
        help="Path to the input JSONL file containing the Faktencheck database created "
        "with `db_converter.py`.",
    )
    parser.add_argument(
        "-s",
        "--key-sep",
        type=str,
        default=".",
        help="Separator to use when joining nested keys.",
    )
    parser.add_argument(
        "-n",
        "--top-n",
        type=int,
        default=20,
        help="Number of unique entries threshold for displaying keys.",
    )
    args = parser.parse_args()
    kwargs = vars(args)

    show_unique_values_summary(**kwargs)
