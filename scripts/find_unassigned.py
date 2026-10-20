#!/usr/bin/env python3
"""Copy PDFs from the main folder that are not in any split into splits/unassigned.

Checks every PDF in 'zotero_literaturdatenbank' against splits/train, dev, test
and unlabeled (matched by file name). Files found in none of them are copied
to splits/unassigned.

Usage:
    python find_unassigned.py                      # run from the folder that contains both
    python find_unassigned.py --base /path/to/data
    python find_unassigned.py --dry-run            # only list what would be copied
"""
import argparse
import shutil
from pathlib import Path

SPLITS = ("train", "dev", "test", "unlabeled")


def pdf_names(folder: Path) -> set[str]:
    return {p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=Path("."), help="folder containing the main folder and splits/")
    ap.add_argument("--main", default="zotero_literaturdatenbank", help="name of the main PDF folder")
    ap.add_argument("--splits", default="splits", help="name of the splits folder")
    ap.add_argument("--dry-run", action="store_true", help="only report, don't copy")
    args = ap.parse_args()

    main_dir = args.base / args.main
    splits_dir = args.base / args.splits
    target = splits_dir / "unassigned"

    if not main_dir.is_dir():
        raise SystemExit(f"Main folder not found: {main_dir}")

    assigned: set[str] = set()
    for s in SPLITS:
        d = splits_dir / s
        if not d.is_dir():
            raise SystemExit(f"Split folder not found: {d}")
        names = pdf_names(d)
        print(f"{s:10s}: {len(names)} PDFs")
        assigned |= names

    all_pdfs = sorted(pdf_names(main_dir))
    new = [n for n in all_pdfs if n not in assigned]
    print(f"{args.main}: {len(all_pdfs)} PDFs, {len(new)} not in any split")

    # Sanity check: files in splits that aren't in the main folder
    orphans = assigned - set(all_pdfs)
    if orphans:
        print(f"Note: {len(orphans)} PDF(s) in splits are missing from {args.main}, e.g. {sorted(orphans)[:5]}")

    if not new:
        return
    if args.dry_run:
        print("\nWould copy:")
        for n in new:
            print("  " + n)
        return

    target.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    for n in new:
        dst = target / n
        if dst.exists():
            skipped += 1
            continue
        shutil.copy2(main_dir / n, dst)
        copied += 1
    print(f"\nCopied {copied} file(s) to {target}" + (f" ({skipped} already there)" if skipped else ""))


if __name__ == "__main__":
    main()
