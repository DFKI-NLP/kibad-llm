"""Align a newer ösl_papers_ids-style CSV export with the formatting conventions of the currently
committed `data/external/ecosystem_services/ösl_papers_ids.csv`.

The formatting differences this script corrects were identified by comparing
`ösl_papers_ids.csv` (committed) with a newer export received from JM, `ösl_papers_ids_JM.csv`:

- Two columns were renamed earlier in this project so their names are valid Python identifiers
  matching `EcosystemServiceFields` in `src/kibad_llm/schema/types.py` ("Biodiv-Facette" ->
  "Biodiv_Facette", "Art(en)" -> "Arten"); newer raw exports still use the original names.
- Newer exports may carry extra columns (e.g. review-tracking metadata) not present in the
  committed file.
- Newer exports preserve Unicode punctuation (hyphen/dash/quote variants) that the committed file
  has flattened to their ASCII equivalents.

This script does *not* touch line endings - the committed file is CRLF, but newer exports are left
as-is (LF), per the decision recorded when this script was written.

This is a one-off/standalone script, not part of the extraction pipeline - see
`docs/CONTRIBUTING.md` for where `data_integration/` scripts fit in the project layout.
"""

import argparse
import csv
from pathlib import Path
import re

from loguru import logger

from kibad_llm.config import DATA_DIR

# Columns renamed in this project (see commit "change english terms in schema to german to fit
# column names of csv") to match `EcosystemServiceFields` field names. Newer raw exports still use
# the original column names on the left.
COLUMN_RENAMES = {
    "Biodiv-Facette": "Biodiv_Facette",
    "Art(en)": "Arten",
}

# Unicode punctuation variants seen in newer exports, mapped to the ASCII equivalents already used
# throughout the committed file.
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


def align_csv(input_path: Path, reference_path: Path, output_path: Path) -> None:
    """Align `input_path`'s CSV formatting with `reference_path`'s conventions and write the
    result to `output_path`.

    Applies, in order: column renames (see `COLUMN_RENAMES`), then restricts and reorders columns
    to exactly match `reference_path`'s header, then normalizes Unicode punctuation to ASCII (see
    `PUNCTUATION_NORMALIZATION`) on every cell. Line endings are left as `input_path` has them.

    Args:
        input_path: CSV file to align (e.g. a newer export).
        reference_path: CSV file whose column set/order to align to.
        output_path: Where to write the aligned CSV.

    Raises:
        ValueError: If, after applying `COLUMN_RENAMES`, `input_path` is missing a column that
            `reference_path` has.
    """
    with open(reference_path, newline="", encoding="utf-8") as f:
        reference_columns = next(csv.reader(f))

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        renamed_fieldnames = [COLUMN_RENAMES.get(c, c) for c in reader.fieldnames or []]
        missing = [c for c in reference_columns if c not in renamed_fieldnames]
        if missing:
            raise ValueError(
                f"{input_path} is missing column(s) present in {reference_path}: {missing}"
            )
        aligned_rows = []
        for row in reader:
            renamed_row = {COLUMN_RENAMES.get(k, k): v for k, v in row.items()}
            aligned_rows.append(
                {col: normalize_punctuation(renamed_row[col]) for col in reference_columns}
            )

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=reference_columns, lineterminator="\n")
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
        default=DATA_DIR / "external" / "ecosystem_services" / "ösl_papers_ids_JM.csv",
        help="Newer CSV export to align.",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=DATA_DIR / "external" / "ecosystem_services" / "ösl_papers_ids.csv",
        help="CSV file whose column set/order to align to.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "external" / "ecosystem_services" / "ösl_papers_ids_JM_aligned.csv",
        help="Where to write the aligned CSV. Does not overwrite --reference by default.",
    )
    args = parser.parse_args()
    align_csv(input_path=args.input, reference_path=args.reference, output_path=args.output)
