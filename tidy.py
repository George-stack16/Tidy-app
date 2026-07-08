#!/usr/bin/env python3
"""
tidy.py — a small, precise utility with two jobs:

1. organize  — sorts files in a folder into subfolders by type,
               renaming any messy/duplicate filenames along the way.
2. clean     — cleans a messy CSV or text file: strips whitespace,
               removes blank/duplicate rows, normalizes headers,
               fixes encoding issues.

USAGE
-----
  python tidy.py organize /path/to/folder
  python tidy.py organize /path/to/folder --dry-run
  python tidy.py clean data.csv
  python tidy.py clean data.csv --output clean_data.csv

No external dependencies — pure Python 3 standard library.
"""

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

# ----------------------------------------------------------------------
# Category map for organize command. Add/edit extensions freely.
# ----------------------------------------------------------------------
CATEGORIES = {
    "images":    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".heic"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt"},
    "spreadsheets": {".xlsx", ".xls", ".csv", ".tsv"},
    "presentations": {".ppt", ".pptx", ".key"},
    "audio":     {".mp3", ".wav", ".flac", ".m4a"},
    "video":     {".mp4", ".mov", ".avi", ".mkv"},
    "archives":  {".zip", ".rar", ".tar", ".gz", ".7z"},
    "code":      {".py", ".js", ".ts", ".html", ".css", ".json", ".sh"},
}


def clean_filename(name: str) -> str:
    """Turn a messy filename into a clean, consistent one.

    'My Photo (2)  FINAL.JPG' -> 'my_photo_2_final.jpg'
    """
    stem, ext = Path(name).stem, Path(name).suffix.lower()
    stem = stem.strip().lower()
    stem = re.sub(r"[^\w\-]+", "_", stem)   # non-word chars -> underscore
    stem = re.sub(r"_+", "_", stem).strip("_")
    return f"{stem}{ext}" if stem else f"unnamed{ext}"


def category_for(ext: str) -> str:
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "other"


def unique_path(target: Path) -> Path:
    """Avoid overwriting: file.txt -> file_1.txt -> file_2.txt ..."""
    if not target.exists():
        return target
    stem, ext, parent = target.stem, target.suffix, target.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{ext}"
        if not candidate.exists():
            return candidate
        i += 1


def organize(folder: str, dry_run: bool = False) -> None:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"Error: '{root}' is not a folder.")

    moved, skipped = 0, 0
    for item in sorted(root.iterdir()):
        if item.is_dir():
            continue  # don't touch existing subfolders

        ext = item.suffix.lower()
        category = category_for(ext)
        new_name = clean_filename(item.name)
        dest_dir = root / category
        dest_path = unique_path(dest_dir / new_name)

        action = f"{item.name}  ->  {category}/{dest_path.name}"
        if dry_run:
            print(f"[dry-run] {action}")
        else:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(dest_path))
            print(action)
        moved += 1

    if moved == 0:
        print("Nothing to organize — folder is already clean or empty.")
    else:
        verb = "Would move" if dry_run else "Moved"
        print(f"\n{verb} {moved} file(s) into {len(CATEGORIES) + 1} possible categories.")


def normalize_header(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^\w]+", "_", name)
    return re.sub(r"_+", "_", name).strip("_") or "column"


def clean_data(input_path: str, output_path: str | None) -> None:
    src = Path(input_path).expanduser().resolve()
    if not src.is_file():
        sys.exit(f"Error: '{src}' is not a file.")

    dest = Path(output_path).expanduser().resolve() if output_path else src.with_name(
        f"{src.stem}_clean{src.suffix or '.csv'}"
    )

    # Try common encodings so odd exports don't crash the script.
    raw_bytes = src.read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        sys.exit("Error: could not decode file with utf-8 or latin-1.")

    # Sniff delimiter; default to comma.
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(text.splitlines(), dialect))
    if not rows:
        sys.exit("Error: file has no rows.")

    header = [normalize_header(h) for h in rows[0]]
    body = rows[1:]

    cleaned, seen = [], set()
    dropped_blank = dropped_dupe = 0

    for row in body:
        row = [cell.strip() for cell in row]
        if not any(row):                 # fully blank row
            dropped_blank += 1
            continue
        # pad/truncate to header length so downstream tools don't choke
        if len(row) < len(header):
            row += [""] * (len(header) - len(row))
        elif len(row) > len(header):
            row = row[: len(header)]
        key = tuple(row)
        if key in seen:                  # exact duplicate row
            dropped_dupe += 1
            continue
        seen.add(key)
        cleaned.append(row)

    # Drop columns that are empty across every remaining row.
    keep_idx = [
        i for i in range(len(header))
        if any(row[i] for row in cleaned)
    ]
    header = [header[i] for i in keep_idx]
    cleaned = [[row[i] for i in keep_idx] for row in cleaned]

    with dest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned)

    print(f"Cleaned data written to: {dest}")
    print(f"  Rows kept:            {len(cleaned)}")
    print(f"  Blank rows removed:   {dropped_blank}")
    print(f"  Duplicate rows removed: {dropped_dupe}")
    print(f"  Columns kept:         {len(header)} / {len(rows[0])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize files in a folder, or clean a messy CSV/text file."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_org = sub.add_parser("organize", help="Sort a folder's files into subfolders by type.")
    p_org.add_argument("folder", help="Path to the folder to organize.")
    p_org.add_argument("--dry-run", action="store_true", help="Preview without moving files.")

    p_clean = sub.add_parser("clean", help="Clean a messy CSV/text file.")
    p_clean.add_argument("file", help="Path to the CSV/text file to clean.")
    p_clean.add_argument("--output", help="Path for the cleaned file (default: <name>_clean.csv).")

    args = parser.parse_args()

    if args.command == "organize":
        organize(args.folder, dry_run=args.dry_run)
    elif args.command == "clean":
        clean_data(args.file, args.output)


if __name__ == "__main__":
    main()