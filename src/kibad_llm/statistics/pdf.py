#!/usr/bin/env python3
"""Summarize PDF pages and markdown characters, optionally grouped by metadata."""

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
    print(f"Warning: {message}", file=sys.stderr)


def add_unique(index, key, value, source):
    """Accept identical duplicates; fail on conflicting content."""
    if key in index and index[key] != value:
        raise ValueError(f"{source}: conflicting content for {key!r}")
    index[key] = value


def read_markdown(paths):
    """Index markdown text by PDF filename; ignore other prediction fields."""
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
    """Count pages using the selected PDF reader."""
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
    """Join PDFs to metadata and markdown, then keep only aggregate counts."""
    metadata = {}
    with args.metadata.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if "Key" not in columns:
            raise ValueError("Metadata CSV must have a 'Key' column")
        if args.group_by and args.group_by not in ["pdf-path", *columns]:
            raise ValueError(f"Unknown --group-by {args.group_by!r}; choose pdf-path or {columns}")
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
            if key not in metadata:
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
    """Print totals and group shares as a Markdown table."""
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
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Matching and counting:
  PDF stem = metadata CSV 'Key'; PDF filename = JSONL 'file_name'.
  Characters = len(JSONL 'text'), including whitespace and markdown syntax.
  Identical metadata rows or markdown texts for a key are accepted; conflicts
  raise an error. Other JSONL fields are ignored. Duplicate PDF stems warn and
  keep the first PDF, in input-folder order then sorted path order.
  Missing metadata/markdown fails unless --skip-missing-metadata-or-md is set.
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
    parser.add_argument("--metadata", type=Path, required=True, metavar="CSV", help="Metadata CSV")
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
        help="Warn and skip PDFs missing metadata or markdown (default: fail)",
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
    args = parse_args()
    report = collect(args)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)


if __name__ == "__main__":
    main()
