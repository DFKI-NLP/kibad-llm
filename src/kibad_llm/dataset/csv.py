import pandas as pd


def remove_nan_from_dict(d: dict) -> dict:
    """Remove keys with NaN values from a dictionary."""
    return {k: v for k, v in d.items() if not pd.isna(v)}


def read_grouped_csv_records(
    file: str,
    output_key: str,
    pdf_id_column: str = "Key",
    columns: list[str] | None = None,
    remove_nan: bool = True,
) -> dict[str, dict[str, list]]:
    """Read grouped compound entries (e.g. organism trends, ecosystem service trends) from a CSV
    file. There are multiple entries per pdf ID, so they are grouped into lists.

    Args:
        file: Path to the CSV file.
        output_key: The key under which the list of entries is stored for each pdf ID. This should
                    match the corresponding field name in the target schema.
        pdf_id_column: Name of the column containing the pdf IDs.
        columns: Optional list of columns to read from the CSV file. If not provided,
                 all columns are read.
        remove_nan: Whether to remove NaN values from the dictionaries.
    Returns:
        A dictionary mapping pdf IDs to their entries each represented as a list of dictionaries.
    """
    if columns is not None and pdf_id_column not in columns:
        columns = [pdf_id_column] + columns
    df = pd.read_csv(file, usecols=columns)

    # Group by pdf_id_column and convert each group to a list of dictionaries
    result: dict[str, dict[str, list]] = {}
    for pdf_id, group in df.groupby(pdf_id_column):
        # remove the pdf_id_column from the group
        group = group.drop(columns=[pdf_id_column])
        group_dicts = group.to_dict("records")
        if remove_nan:
            group_dicts = [remove_nan_from_dict(d) for d in group_dicts]
        result[str(pdf_id)] = {output_key: group_dicts}

    return result
