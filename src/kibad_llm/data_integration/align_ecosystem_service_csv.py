"""Process the raw ÖSL reference export `data/external/ecosystem_services/wald_devset_raw.csv`
into the format used as reference data for the ecosystem service evaluation.

The script corrects the following formatting differences of the raw export:

- Columns are renamed so their names are valid Python identifiers matching
  `EcosystemServiceFields` in `src/kibad_llm/schema/types.py` ("Biodiv-Facette" ->
  "Biodiv_Facette", "Art(en)" -> "Arten"); the raw export uses the original names. The title
  column is accepted both as "Title" and "title" and written as "Title".
- The raw export carries extra columns (e.g. review-tracking metadata) that are dropped; the
  columns to keep and their order are defined by `OUTPUT_COLUMNS`.
- The raw export preserves Unicode punctuation (hyphen/dash/quote variants), which is flattened
  to the ASCII equivalents.

Optionally, papers can be filtered (all rows of a paper, identified by "Key") with
`--exclude-methods` (e.g. reviews and pure model studies) and `--require-habitat` (e.g. "Wald"). The
forest dev set reference is created without any filter (it only covers Wald by choice):
```
    uv run -m kibad_llm.data_integration.align_ecosystem_service_csv
```
Example with filters (pass `--output` so the filtered file does not overwrite the default):
```
    uv run -m kibad_llm.data_integration.align_ecosystem_service_csv \\
        --exclude-methods Literaturstudie Modell/Simulation --require-habitat Wald \\
        --output path/to/filtered.csv
```
TODO: papers that contain Wald *and* other habitats are currently kept unchanged, see `filter_papers`.
"""

import argparse
from collections.abc import Collection
import csv
from pathlib import Path
import re

from loguru import logger

from kibad_llm.config import EXTERNAL_DATA_DIR, INTERIM_DATA_DIR

# Columns renamed in this project (see commit "change english terms in schema to german to fit
# column names of csv") to match `EcosystemServiceFields` field names. The raw export uses the
# original column names on the left.
COLUMN_RENAMES = {
    "Biodiv-Facette": "Biodiv_Facette",
    "Art(en)": "Arten",
    "title": "Title",
}

# Columns (after applying `COLUMN_RENAMES`) written to the output, in this order. Further columns of
# the raw export (e.g. review-tracking metadata) are dropped.
OUTPUT_COLUMNS = [
    "Key",
    "Title",
    "Ja",
    "authors",
    "journal",
    "abstract",
    "year",
    "doi",
    "Quelle",
    "Themenkomplex",
    "ÖSL",
    "Biodiv_Facette",
    "Einfluss",
    "Methode",
    "Notiz zum Vote Count",
    "Ort",
    "Ort Details",
    "Lebensraum",
    "Arten",
    "Ökologische Einheit",
    "Artengruppe",
    "ESGroup",
    "Boden?",
    "Lebensraum_Gruppiert",
    "CICES-Bereich",
    "CICES-Gruppe",
    "CICES-Klasse",
    "CICES-Code",
    "Bereich-Kurz",
    "Klasse kurz",
]

# Cell values renamed per column so they match the vocabulary of the corresponding schema enum.
# "Lebensraum_Gruppiert" must match `HabitatEnum`, which uses the plural "Küsten".
VALUE_RENAMES = {
    "Lebensraum_Gruppiert": {"Küste und Küstengewässer": "Küsten und Küstengewässer"},
}

# Unicode punctuation variants seen in the raw export, mapped to their ASCII equivalents.
PUNCTUATION_NORMALIZATION = {
    "‐": "-",  # HYPHEN
    "‑": "-",  # NON-BREAKING HYPHEN
    "‒": "-",  # FIGURE DASH
    "–": "-",  # EN DASH
    "—": "-",  # EM DASH
    "‘": "'",  # LEFT SINGLE QUOTATION MARK
    "’": "'",  # RIGHT SINGLE QUOTATION MARK
    "“": '"',  # LEFT DOUBLE QUOTATION MARK
    "”": '"',  # RIGHT DOUBLE QUOTATION MARK
}
_PUNCTUATION_PATTERN = re.compile("|".join(re.escape(c) for c in PUNCTUATION_NORMALIZATION))


def normalize_punctuation(value: str) -> str:
    """Replace Unicode hyphen/dash/quote variants in `value` with their ASCII equivalents.

    Args:
        value: Cell value to normalize.

    Returns:
        The normalized value. Falsy values (e.g. `""`) are returned unchanged.
    """
    if not value:
        return value
    return _PUNCTUATION_PATTERN.sub(lambda m: PUNCTUATION_NORMALIZATION[m.group(0)], value)


def rename_value(column: str, value: str) -> str:
    """Apply the `VALUE_RENAMES` for `column` to `value`.

    Multi-valued cells (comma-separated, e.g. "Wald, Küste und Küstengewässer") are renamed
    element-wise.

    Args:
        column: Name of the (already renamed) column the value belongs to.
        value: Cell value.

    Returns:
        The value with all renames for `column` applied.
    """
    renames = VALUE_RENAMES.get(column)
    if not renames or not value:
        return value
    return ", ".join(renames.get(part.strip(), part.strip()) for part in value.split(","))


def _tokens(value: str) -> set[str]:
    """Split a comma-separated cell into its stripped, non-empty elements.

    Args:
        value: Cell value, e.g. "Feld, Modell/Simulation".

    Returns:
        The set of elements, e.g. `{"Feld", "Modell/Simulation"}`.
    """
    return {part.strip() for part in value.split(",") if part.strip()}


def filter_papers(
    rows: list[dict[str, str]],
    exclude_methods: Collection[str] = (),
    require_habitat: str | None = None,
) -> list[dict[str, str]]:
    """Drop whole papers (all rows sharing a "Key") from `rows` based on method and habitat.

    Both criteria work on the comma-separated elements of a cell, and on the paper level:

    - `exclude_methods`: a paper is dropped if *any* of its rows has an excluded method among the
      elements of its "Methode" cell. "Feld, Modell/Simulation" thus also matches "Modell/Simulation".
    - `require_habitat`: a paper is kept only if *any* of its rows has the habitat among the
      elements of its "Lebensraum_Gruppiert" cell.

    Rows of the papers that are kept are not modified.

    Args:
        rows: Aligned rows; must contain the columns "Key", and "Methode" / "Lebensraum_Gruppiert"
            if the respective criterion is used.
        exclude_methods: "Methode" values whose papers to drop. Empty: no filtering by method.
        require_habitat: "Lebensraum_Gruppiert" value that a paper must contain. `None`: no
            filtering by habitat.

    Returns:
        The rows of the remaining papers, in their original order.

    Raises:
        ValueError: If a column required by a used criterion is missing in `rows`.

    Todo:
        Papers that contain "Wald" *and* other habitats are kept unchanged, i.e. their non-Wald
        rows (and the non-Wald parts of multi-habitat cells, which `split_columns` of the dataset
        config turns into separate rows) remain in the output. Decide whether to (a) drop the
        non-Wald rows of such papers, (b) drop such papers entirely, or (c) keep them as they are.
        The prompt only extracts relations for the habitat "Wald".
    """
    required_columns = ["Key"]
    if exclude_methods:
        required_columns.append("Methode")
    if require_habitat is not None:
        required_columns.append("Lebensraum_Gruppiert")
    if rows:
        missing = [c for c in required_columns if c not in rows[0]]
        if missing:
            raise ValueError(f"Cannot filter papers, missing column(s): {missing}")

    excluded = set(exclude_methods)
    dropped_by_method: set[str] = set()
    keys_with_habitat: set[str] = set()
    for row in rows:
        if excluded and _tokens(row["Methode"]) & excluded:
            dropped_by_method.add(row["Key"])
        if require_habitat is not None and require_habitat in _tokens(row["Lebensraum_Gruppiert"]):
            keys_with_habitat.add(row["Key"])

    all_keys = {row["Key"] for row in rows}
    dropped_by_habitat = (
        set() if require_habitat is None else all_keys - keys_with_habitat - dropped_by_method
    )
    if dropped_by_method:
        logger.info(
            f"Dropping {len(dropped_by_method)} paper(s) with Methode in {sorted(excluded)}: "
            f"{sorted(dropped_by_method)}"
        )
    if dropped_by_habitat:
        logger.info(
            f"Dropping {len(dropped_by_habitat)} paper(s) without habitat '{require_habitat}'"
        )
    dropped = dropped_by_method | dropped_by_habitat
    return [row for row in rows if row["Key"] not in dropped]


def align_csv(
    input_path: Path,
    output_path: Path,
    exclude_methods: Collection[str] = (),
    require_habitat: str | None = None,
) -> None:
    """Align `input_path`'s CSV formatting with the conventions of the reference data and write the
    result to `output_path`.

    Applies, in order: column renames (see `COLUMN_RENAMES`), then restricts and reorders columns
    to exactly match `OUTPUT_COLUMNS`, then normalizes Unicode punctuation to ASCII (see
    `PUNCTUATION_NORMALIZATION`) and renames selected values (see `VALUE_RENAMES`) on every cell.
    Finally, papers are optionally filtered (see `filter_papers`). Line endings are written as LF.
    The parent directory of `output_path` is created if necessary.

    Args:
        input_path: CSV file to align (the raw export).
        output_path: Where to write the aligned CSV.
        exclude_methods: Drop papers with one of these "Methode" values, see `filter_papers`.
        require_habitat: Keep only papers with this "Lebensraum_Gruppiert" value, see
            `filter_papers`.

    Raises:
        ValueError: If, after applying `COLUMN_RENAMES`, `input_path` is missing a column of
            `OUTPUT_COLUMNS`, or if a column needed for filtering is missing in the output.
    """
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        renamed_fieldnames = [COLUMN_RENAMES.get(c, c) for c in reader.fieldnames or []]
        missing = [c for c in OUTPUT_COLUMNS if c not in renamed_fieldnames]
        if missing:
            raise ValueError(f"{input_path} is missing column(s): {missing}")
        aligned_rows = []
        for row in reader:
            renamed_row = {COLUMN_RENAMES.get(k, k): v for k, v in row.items()}
            aligned_rows.append(
                {
                    col: rename_value(col, normalize_punctuation(renamed_row[col]))
                    for col in OUTPUT_COLUMNS
                }
            )

    n_rows_before = len(aligned_rows)
    aligned_rows = filter_papers(
        aligned_rows, exclude_methods=exclude_methods, require_habitat=require_habitat
    )
    if len(aligned_rows) != n_rows_before:
        logger.info(f"Filtering kept {len(aligned_rows)} of {n_rows_before} rows")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(aligned_rows)

    logger.info(f"Wrote {len(aligned_rows)} aligned rows to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=EXTERNAL_DATA_DIR / "ecosystem_services" / "wald_devset_raw.csv",
        help="Raw CSV export to align.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=INTERIM_DATA_DIR / "ecosystem_services" / "wald_devset_processed.csv",
        help="Where to write the aligned CSV. The default name fits the unfiltered forest dev "
        "set; pass --output when using filters.",
    )
    parser.add_argument(
        "--exclude-methods",
        nargs="+",
        default=[],
        metavar="METHODE",
        help="Drop papers that contain one of these 'Methode' values, e.g. Literaturstudie "
        "Modell/Simulation (reviews and pure model studies). Values are matched against the "
        "comma-separated elements of the cell, so 'Feld, Modell/Simulation' matches as well.",
    )
    parser.add_argument(
        "--require-habitat",
        default=None,
        metavar="LEBENSRAUM",
        help="Keep only papers that contain this 'Lebensraum_Gruppiert' value, e.g. Wald. "
        "TODO: papers that contain Wald and other habitats are kept unchanged, see filter_papers.",
    )
    args = parser.parse_args()
    align_csv(
        input_path=args.input,
        output_path=args.output,
        exclude_methods=args.exclude_methods,
        require_habitat=args.require_habitat,
    )
