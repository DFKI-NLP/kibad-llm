#!/usr/bin/env python3
"""Split a JSONL metadata file into train/dev/test according to where each PDF lives.

Each line must contain the key "zotitem_ptr_id". Its value + ".pdf" is looked up
in the train, dev and test folders; the original line is written to
train.jsonl, dev.jsonl or test.jsonl accordingly.

Usage:
    python split_jsonl.py metadata.jsonl --pdf-root data/ --out-dir out/
    python split_jsonl.py metadata.jsonl --train data/train --dev data/dev --test data/test
"""
import argparse
import json
from pathlib import Path
import sys

SPLITS = ("train", "dev", "test")


def list_pdfs(folder: Path) -> set[str]:
    if not folder.is_dir():
        sys.exit(f"Folder not found: {folder}")
    return {p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("jsonl", type=Path, help="input JSONL file")
    ap.add_argument(
        "--pdf-root", type=Path, help="folder containing train/, dev/, test/ subfolders"
    )
    for s in SPLITS:
        ap.add_argument(f"--{s}", type=Path, help=f"{s} PDF folder (overrides --pdf-root)")
    ap.add_argument(
        "--out-dir", type=Path, default=Path("."), help="where to write train/dev/test.jsonl"
    )
    ap.add_argument("--key", default="zotitem_ptr_id", help="JSON key holding the file id")
    args = ap.parse_args()

    # Resolve the three PDF folders
    folders = {}
    for s in SPLITS:
        folder = getattr(args, s) or (args.pdf_root / s if args.pdf_root else None)
        if folder is None:
            ap.error(f"Specify --pdf-root or --{s}")
        folders[s] = folder

    # Index PDF names per split (one directory listing each, fast for big folders)
    index = {s: list_pdfs(f) for s, f in folders.items()}

    args.out_dir.mkdir(parents=True, exist_ok=True)
    outs = {s: open(args.out_dir / f"{s}.jsonl", "w", encoding="utf-8") for s in SPLITS}
    counts = {s: 0 for s in SPLITS}
    missing, ambiguous, bad = [], [], []

    try:
        with open(args.jsonl, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    file_id = record[args.key]
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    bad.append((lineno, repr(e)))
                    continue

                filename = f"{file_id}.pdf"
                hits = [s for s in SPLITS if filename in index[s]]

                if not hits:
                    missing.append(filename)
                    continue
                if len(hits) > 1:
                    ambiguous.append((filename, hits))
                    continue

                # Write the original line unchanged
                outs[hits[0]].write(line if line.endswith("\n") else line + "\n")
                counts[hits[0]] += 1
    finally:
        for fh in outs.values():
            fh.close()

    # Report
    for s in SPLITS:
        print(f"{s:5s}: {counts[s]} records -> {args.out_dir / (s + '.jsonl')}")
    if missing:
        print(f"\n{len(missing)} PDF(s) not found in any split, e.g.: {missing[:5]}")
    if ambiguous:
        print(
            f"\n{len(ambiguous)} PDF(s) found in more than one split (skipped), e.g.: {ambiguous[:5]}"
        )
    if bad:
        print(f"\n{len(bad)} malformed line(s) or missing key, e.g.: {bad[:5]}")


if __name__ == "__main__":
    main()
