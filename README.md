# Tidy-app

Tidy-app is a small, dependency-free Python utility that helps keep files and data neat.

- `organize`: sorts files into type-based folders and cleans filenames
- `clean`: cleans messy CSV/text files by normalizing headers, removing blank/duplicate rows, and fixing encoding issues

## Features

- No external dependencies — works with Python 3 standard library only
- Automatic file categorization for images, documents, audio, video, archives, code, and more
- Duplicate-safe filename handling during file moves
- Flexible CSV/text cleaning with header normalization and blank row removal

## Usage

```bash
python tidy.py organize /path/to/folder
python tidy.py organize /path/to/folder --dry-run
python tidy.py clean data.csv
python tidy.py clean data.csv --output clean_data.csv
```

## Notes

- The script preserves existing subfolders while organizing files
- Cleaned files are written to a new path by default when using `clean`
