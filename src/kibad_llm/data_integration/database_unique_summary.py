import json
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def main(data_path: str) -> dict[str, dict]:
    """
    Reads the jsonl converted Faktencheck database and extracts unique values.
    Some columns have nested entries, e.g. "direct_driver", these are a list of a dict.
    The database is flattened and the column name combined with the key to generate uniques for the values.
    Should the database or conversion change the columns, they need to be changed manually.

    :param data_path: path to Faktencheck database conversion (.jsonl)
    :return: dictionary with unique values for each (sub-)column
    """
    df = pd.read_json(data_path, lines=True)

    str_cols = [
        "zotitem_ptr_id",
        "status",
        "bibtex_author",
        "bibtex_title",
        "bibtex_year",
        "bibtex_type",
    ]
    list_cols = [
        "biodiversity_level",
        "biodiversity_variable",
        "climate",
        "habitat",
        "landuse",
        "measure",
        "method",
        "natural_region",
        "study_type",
        "transformation_potential",
    ]
    list_of_dict_cols = [
        "conservation_area",
        "direct_driver",
        "ecosystem_service",
        "ecosystem_type",
        "impulse_measure",
        "indirect_driver",
        "location",
        "management_measure",
        "soil",
        "taxa",
    ]

    unique_dict = {}

    for col in str_cols:
        unique_dict[col] = df[col].unique().tolist()

    for col in list_cols:
        unique_dict[col] = df[col].explode().unique().tolist()

    for col in list_of_dict_cols:
        normalized_df = pd.json_normalize(df[col].explode())  # type: ignore
        normalized_df = normalized_df.replace({float("nan"): None})
        sub_cols = normalized_df.columns.to_list()
        for sub_col in sub_cols:
            unique_dict[f"{col}.{sub_col}"] = normalized_df[sub_col].unique().tolist()

    return unique_dict


if __name__ == "__main__":
    # show info level logs
    logging.basicConfig(level=logging.INFO)

    # get unique entries
    unique_dict = main("data/interim/faktencheck-db/faktencheck-db-converted_2025-08-19.jsonl")

    # show numbers on console
    unique_dict_len = {dict_name: len(dict_list) for dict_name, dict_list in unique_dict.items()}
    logger.info(
        f"number of unique entries per key:\n{json.dumps(unique_dict_len, indent=2, sort_keys=True)}\n"
    )

    n = 20
    unique_dict_less_k = {
        k: unique_dict[k] for k in sorted(unique_dict) if len(unique_dict[k]) < n
    }
    # sort entries for better readability
    unique_dict_less_k_sorted = dict(
        sorted(unique_dict_less_k.items(), key=lambda item: len(item[1]))
    )
    # lines = "\n".join(f'{k}: {v}' for k, v in unique_dict_less_k_sorted.items())
    lines = json.dumps(unique_dict_less_k_sorted, indent=2, sort_keys=True, ensure_ascii=False)
    logger.info(
        f"show unique entries for {len(unique_dict_less_k_sorted)} keys with less "
        f"than {n} entries sorted by number of entries (#remaining keys: "
        f"{len(unique_dict_len) - len(unique_dict_less_k_sorted)}):\n{lines}"
    )
