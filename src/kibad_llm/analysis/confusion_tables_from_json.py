#!/usr/bin/env python3
"""Build markdown confusion tables from raw multirun JSON results.

Input format is expected to match job_return_value.json where each top-level entry
is one run with confusion rows plus metadata blocks.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Any

SPECIAL_LAST_ROW = "UNASSIGNABLE"
SPECIAL_LAST_COL = "UNDETECTED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_json", type=Path, help="Path to job_return_value.json from hydra multirun"
    )
    parser.add_argument(
        "--group-by",
        nargs="+",
        default=["prediction.overrides.extractor/llm"],
        help=(
            "One or more dotted key paths used for grouping "
            "(default: prediction.overrides.extractor/llm)"
        ),
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=0,
        help="Rounding precision for mean/std values (default: 0)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output markdown file. Prints to stdout when omitted.",
    )
    return parser.parse_args()


def get_dotted(data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_key)
        current = current[part]
    return current


def extract_confusion(run_payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    confusion: dict[str, dict[str, float]] = {}
    for row_label, row_payload in run_payload.items():
        if not isinstance(row_payload, dict):
            continue
        if row_label in {"prediction", "overrides"}:
            continue

        row_counts: dict[str, float] = {}
        for col_label, value in row_payload.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                row_counts[col_label] = float(value)
        if row_counts:
            confusion[row_label] = row_counts
    return confusion


def move_special_last(items: list[str], special: str) -> list[str]:
    ordered = sorted(x for x in items if x != special)
    if special in items:
        ordered.append(special)
    return ordered


def simplify_group_key(group_key: str) -> str:
    return group_key.split(".")[-1]


def fmt_number(value: float, precision: int) -> str:
    rounded = round(value, precision)
    if abs(rounded) == 0:
        rounded = 0.0
    text = f"{rounded:.{precision}f}" if precision > 0 else str(int(round(rounded)))
    if precision > 0:
        text = text.rstrip("0").rstrip(".")
    return text


def build_markdown_table(
    group_labels: list[tuple[str, str]],
    cell_series: dict[tuple[str, str], list[float]],
    row_labels: list[str],
    col_labels: list[str],
    precision: int,
) -> str:
    lines: list[str] = []
    heading = ", ".join(f"{key}: {value}" for key, value in group_labels)
    lines.append(f"### {heading}")
    lines.append("")

    header = [""] + col_labels
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join([":--"] + ["--:" for _ in col_labels]) + "|")

    for row_label in row_labels:
        row_values: list[str] = []
        for col_label in col_labels:
            values = cell_series.get((row_label, col_label), [])
            if not values:
                row_values.append("0")
                continue

            m = mean(values)
            s = stdev(values) if len(values) > 1 else 0.0
            if math.isnan(m) or math.isnan(s):
                row_values.append("0")
            else:
                row_values.append(f"{fmt_number(m, precision)}±{fmt_number(s, precision)}")

        lines.append("| " + row_label + " | " + " | ".join(row_values) + " |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))

    grouped_runs: dict[tuple[str, ...], list[dict[str, dict[str, float]]]] = {}

    for run_name, run_payload in payload.items():
        if not isinstance(run_payload, dict):
            continue

        group_values: list[str] = []
        for group_key in args.group_by:
            try:
                group_values.append(str(get_dotted(run_payload, group_key)))
            except KeyError:
                raise KeyError(f"Missing group key '{group_key}' in run '{run_name}'") from None

        grouped_runs.setdefault(tuple(group_values), []).append(extract_confusion(run_payload))

    sections: list[str] = []
    for group_values in sorted(grouped_runs):
        runs = grouped_runs[group_values]

        all_rows: set[str] = set()
        all_cols: set[str] = set()
        for confusion in runs:
            all_rows.update(confusion.keys())
            for row in confusion.values():
                all_cols.update(row.keys())

        # Keep columns aligned with known classes even when a class was never predicted.
        all_cols.update(r for r in all_rows if r != SPECIAL_LAST_ROW)

        row_labels = move_special_last(list(all_rows), SPECIAL_LAST_ROW)
        col_labels = move_special_last(list(all_cols), SPECIAL_LAST_COL)

        # Build full aligned per-cell series (missing values are treated as 0).
        cell_series: dict[tuple[str, str], list[float]] = {
            (r, c): [] for r in row_labels for c in col_labels
        }
        for confusion in runs:
            for row_label in row_labels:
                row_payload = confusion.get(row_label, {})
                for col_label in col_labels:
                    value = row_payload.get(col_label, 0.0)
                    cell_series[(row_label, col_label)].append(float(value))

        sections.append(
            build_markdown_table(
                group_labels=[
                    (simplify_group_key(group_key), group_value)
                    for group_key, group_value in zip(args.group_by, group_values)
                ],
                cell_series=cell_series,
                row_labels=row_labels,
                col_labels=col_labels,
                precision=args.precision,
            )
        )

    output = "\n".join(sections).rstrip() + "\n"
    if args.output is None:
        print(output, end="")
    else:
        args.output.write_text(output, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
