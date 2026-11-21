#!/usr/bin/env python3
"""Summarize PDF pages and markdown characters, optionally grouped by metadata.

Attributes:
    METRICS (tuple[str, ...]): Count fields included in totals and groups.

Functions:
    warn: Write a warning to standard error.
    add_unique: Accept identical duplicate values and reject conflicts.
    read_markdown: Load markdown texts from JSONL files and folders.
    count_pages: Count pages with PyMuPDF or a standard-library approximation.
    collect: Join inputs and aggregate counts and percentages.
    print_markdown: Render a report as a Markdown table.
    parse_args: Parse the command-line arguments.
    main: Print the requested aggregate report.
"""

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
import re
import sys

METRICS = ("documents", "pages", "markdown_characters")


def warn(message):
    """Write a warning to standard error.

    Args:
        message (str): Warning text without the severity prefix.
    """
    print(f"Warning: {message}", file=sys.stderr)


def add_unique(index, key, value, source):
    """Accept identical duplicates; fail on conflicting content.

    Args:
        index (dict): Mapping to update in place.
        key (str): Metadata key or PDF filename.
        value (str | dict): Markdown text or metadata row to associate with the key.
        source (str | Path): Input location to include in an error message.

    Raises:
        ValueError: The key already has a different value.
    """
    if key in index and index[key] != value:
        raise ValueError(f"{source}: conflicting content for {key!r}")
    index[key] = value


def read_markdown(paths):
    """Index markdown text by PDF filename; ignore other prediction fields.

    Args:
        paths (list[Path]): JSONL or JSONL.GZ files, or folders to search recursively.

    Returns:
        markdown (dict[str, str]): Texts keyed by the JSONL records' PDF filenames.

    Raises:
        ValueError: An explicit file has an unsupported extension, or duplicate
            filenames have conflicting markdown texts.
        TypeError: A record's text is not a string.
    """
    markdown = {}
    for path in paths:
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for file in files:
            if not file.name.endswith((".jsonl", ".jsonl.gz")):
                if file == path:
                    raise ValueError(f"Expected .jsonl, .jsonl.gz, or a folder: {file}")
                continue
            if file.is_dir():
                continue
            opener = gzip.open if file.suffix == ".gz" else open
            with opener(file, "rt", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    record = json.loads(line)
                    source = f"{file}:{line_number}"
                    text = record["text"]
                    if not isinstance(text, str):
                        raise TypeError(f"{source}: 'text' must be a string")
                    add_unique(markdown, record["file_name"], text, source)
    return markdown


def count_pages(path, use_pymupdf):
    """Count pages using the selected PDF reader.

    Args:
        path (Path): PDF file to read.
        use_pymupdf (bool): Use PyMuPDF when true, otherwise count page markers.

    Returns:
        pages (int): Page count from the selected reader.

    Raises:
        ValueError: The standard-library counter finds no uncompressed page markers.

    Warning:
        The standard-library approximation can miss compressed page objects and
        count obsolete revisions. Use PyMuPDF for reliable counts.
    """
    if use_pymupdf:
        import pymupdf

        with pymupdf.open(path) as document:
            return len(document)
    pages = len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))
    if not pages:
        raise ValueError(
            f"{path}: no uncompressed page objects found; use the default PyMuPDF reader"
        )
    return pages


def collect(args):
    """Join PDFs to metadata and markdown, then keep only aggregate counts.

    Metadata matching is performed only when a CSV is supplied. Grouping by a CSV
    column requires metadata; grouping by the input PDF folder is always available.

    Duplicate PDF stems keep the first occurrence and print a warning to standard
    error. Missing matches warn and skip when requested. Selecting the approximate
    page counter also prints a warning to standard error.

    Args:
        args (argparse.Namespace): Options returned by `parse_args`.

    Returns:
        report (dict): Total counts and percentages, the grouping column, and group statistics.
            Percentages use the totals after skipping and deduplication.

    Raises:
        ValueError: A CSV grouping column is requested without metadata, the
            metadata key column or grouping column is invalid, input
            content conflicts, or required metadata or markdown is missing and
            skipping is disabled.
        NotADirectoryError: A PDF input path is not a directory.
    """
    metadata = {}
    if args.metadata is None and args.group_by not in (None, "pdf-path"):
        raise ValueError(f"--group-by {args.group_by!r} requires --metadata")
    if args.metadata is not None:
        with args.metadata.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames or []
            if "Key" not in columns:
                raise ValueError("Metadata CSV must have a 'Key' column")
            if args.group_by and args.group_by not in ["pdf-path", *columns]:
                raise ValueError(
                    f"Unknown --group-by {args.group_by!r}; choose pdf-path or {columns}"
                )
            for row in reader:
                add_unique(metadata, row["Key"], row, args.metadata)
    markdown = read_markdown(args.markdown)
    if not args.use_pymupdf:
        warn(
            "Dependency-free page counts are approximate; compressed objects and PDF revisions "
            "can cause incorrect counts. Use the default PyMuPDF reader for reliable counts."
        )

    total = Counter(dict.fromkeys(METRICS, 0))
    groups = defaultdict(Counter)
    seen = {}
    for folder in args.pdf_paths:
        if not folder.is_dir():
            raise NotADirectoryError(folder)
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() != ".pdf" or not path.is_file():
                continue
            key = path.stem
            if key in seen:
                warn(f"Duplicate PDF {path}; already encountered {seen[key]}; keeping the first")
                continue
            seen[key] = path
            missing = []
            if args.metadata is not None and key not in metadata:
                missing.append("metadata")
            if path.name not in markdown:
                missing.append("markdown")
            if missing:
                message = f"{path}: missing {' and '.join(missing)}"
                if not args.skip_missing_metadata_or_md:
                    raise ValueError(message)
                warn(f"{message}; skipping PDF")
                continue
            counts = dict(
                documents=1,
                pages=count_pages(path, args.use_pymupdf),
                markdown_characters=len(markdown[path.name]),
            )
            total.update(counts)
            if args.group_by:
                group = (
                    str(folder) if args.group_by == "pdf-path" else metadata[key][args.group_by]
                )
                groups[group].update(counts)

    def statistics(counts):
        """Calculate counts and their percentages of the retained totals.

        Args:
            counts (Counter): Counts for the total or one group.

        Returns:
            statistics (dict): Counts and percentage fields, using zero for empty totals.
        """
        return {
            **{metric: counts[metric] for metric in METRICS},
            **{
                f"{metric}_percent": (
                    round(100 * counts[metric] / total[metric], 2) if total[metric] else 0.0
                )
                for metric in METRICS
            },
        }

    return {
        "total": statistics(total),
        "group_by": args.group_by,
        "groups": [{"group": group, **statistics(groups[group])} for group in sorted(groups)],
    }


def print_markdown(report):
    """Print totals and group shares as a Markdown table.

    Args:
        report (dict): Aggregate report returned by `collect`.
    """
    print("| Group | Documents | % | Pages | % | Markdown characters | % |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    rows = [("Total", report["total"])]
    rows.extend((row["group"] or "(empty)", row) for row in report["groups"])
    for label, row in rows:
        label = label.replace("|", r"\|").replace("\r", "").replace("\n", "<br>")
        cells = [label]
        for metric in METRICS:
            cells.extend([str(row[metric]), f"{row[f'{metric}_percent']:.2f}%"])
        print(f"| {' | '.join(cells)} |")


def parse_args(argv=None):
    """Parse the command-line arguments.

    Args:
        argv (list[str] | None): Argument strings, or None to use the process arguments.

    Returns:
        args (argparse.Namespace): Input paths, grouping, output format, and reader options.

    Raises:
        SystemExit: Help was requested or the supplied arguments are invalid.
    """
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Matching and counting:
  PDF stem = metadata CSV 'Key'; PDF filename = JSONL 'file_name'.
  Without --metadata, metadata matching is disabled; only pdf-path grouping
  is available. Grouping by a CSV column requires --metadata.
  Characters = len(JSONL 'text'), including whitespace and markdown syntax.
  Identical metadata rows or markdown texts for a key are accepted; conflicts
  raise an error. Other JSONL fields are ignored. Duplicate PDF stems warn and
  keep the first PDF, in input-folder order then sorted path order.
  Missing markdown or supplied metadata fails unless
  --skip-missing-metadata-or-md is set.
  Empty markdown is valid. Empty CSV group values form a single group.
  Percentages use totals after skipping and deduplication; zero totals give 0%.
  Warnings go to stderr. Output contains aggregates only.

PDF reader:
  PyMuPDF is used by default (install with: python -m pip install pymupdf).
  --dont-use-pymupdf uses only the standard library to count /Type /Page markers.
  This approximation can miss compressed objects or count obsolete revisions.
  It warns when selected and fails if no page markers are found.

Example:
  uv run -m kibad_llm.statistics.pdf \\
    --pdf-path data/cluster-mirror/dev-set-100 \\
    --markdown data/kibad-llm-results/data/processed/faktencheck/dev-set-100 \\
    --metadata metadata.csv --group-by 'Item Type' --format markdown
""",
    )
    parser.add_argument(
        "--pdf-path",
        dest="pdf_paths",
        nargs="+",
        action="extend",
        type=Path,
        required=True,
        metavar="FOLDER",
        help="PDF input folders, searched recursively; may be repeated",
    )
    parser.add_argument(
        "--markdown",
        nargs="+",
        action="extend",
        type=Path,
        required=True,
        metavar="PATH",
        help="JSONL/JSONL.GZ files or recursively searched folders; may be repeated",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        metavar="CSV",
        help="Optional metadata CSV; required for grouping by a CSV column",
    )
    parser.add_argument(
        "--group-by",
        metavar="COLUMN",
        help="Input PDF folder ('pdf-path') or an exact CSV column name",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--skip-missing-metadata-or-md",
        action="store_true",
        help="Warn and skip PDFs missing markdown or supplied metadata (default: fail)",
    )
    parser.add_argument(
        "--dont-use-pymupdf",
        "--dont-use-pymudf",
        dest="use_pymupdf",
        action="store_false",
        help="Use approximate page counts without external libraries (default: use PyMuPDF)",
    )
    return parser.parse_args(argv)


def main():
    """Read process arguments and print an aggregate JSON or Markdown report."""
    args = parse_args()
    report = collect(args)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)


if __name__ == "__main__":
    main()
