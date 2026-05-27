"""
Compress Mini-Project/ into a single .tar.xz archive at maximum compression.

- Format: POSIX tar streamed through LZMA2 (xz) at preset=9 | PRESET_EXTREME.
  Highest ratio available from the Python standard library — no external
  binary required.
- Exclusions: every CLAUDE.md (any case, any depth), plus common cruft
  (.DS_Store, Thumbs.db, __pycache__, .ipynb_checkpoints, .git, .agents,
  *.pyc/.pyo, build aux, the SUBMISSION shortcut folder).
- Output: '<repo>/Rosas-Tiongson - Fuel Agriculture.tar.xz' by default.

Run:
    python scripts/compress_mini_project.py
    python scripts/compress_mini_project.py --output some/other/name
    python scripts/compress_mini_project.py --dry-run    # list what would go in
"""

from __future__ import annotations

import argparse
import lzma
import os
import sys
import tarfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "Mini-Project"
DEFAULT_OUTPUT = REPO_ROOT / "Rosas-Tiongson - Fuel Agriculture.tar.xz"

EXCLUDED_NAMES = {
    "claude.md",
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
}
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".ipynb_checkpoints",
    ".git",
    ".agents",
    ".vscode",
    ".idea",
    "submission",
}
EXCLUDED_SUFFIXES = {
    ".pyc", ".pyo",
    ".aux", ".log", ".nav", ".out", ".snm", ".toc",
    ".synctex.gz",
    ".lnk",
}


def is_excluded(path: Path, source_root: Path) -> bool:
    """True if any path component matches an exclusion rule."""
    rel = path.relative_to(source_root)
    parts_lower = [p.lower() for p in rel.parts]

    for part in parts_lower:
        if part in EXCLUDED_DIR_NAMES:
            return True

    name_lower = path.name.lower()
    if name_lower in EXCLUDED_NAMES:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return False


def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:7.2f} {unit}"
        n /= 1024
    return f"{n:.2f} GB"


def collect_entries(source_root: Path) -> list[Path]:
    entries: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(source_root):
        here = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in EXCLUDED_DIR_NAMES
            and not is_excluded(here / d, source_root)
        ]
        for fname in filenames:
            f = here / fname
            if not is_excluded(f, source_root):
                entries.append(f)
    entries.sort()
    return entries


def build_archive(
    source_root: Path,
    output_path: Path,
    arcname_base: str,
    *,
    preset: int = 9 | lzma.PRESET_EXTREME,
    check: int = lzma.CHECK_SHA256,
) -> tuple[int, int, int]:
    """Returns (file_count, raw_bytes, compressed_bytes)."""
    entries = collect_entries(source_root)
    raw_total = sum(f.stat().st_size for f in entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with lzma.open(
        output_path,
        mode="wb",
        format=lzma.FORMAT_XZ,
        check=check,
        preset=preset,
    ) as xz_stream:
        with tarfile.open(
            fileobj=xz_stream,
            mode="w|",
            format=tarfile.PAX_FORMAT,
            encoding="utf-8",
        ) as tar:
            tar.add(
                source_root,
                arcname=arcname_base,
                recursive=False,
            )

            written = 0
            t0 = time.time()
            for f in entries:
                rel = f.relative_to(source_root)
                arcname = f"{arcname_base}/{rel.as_posix()}"
                tar.add(f, arcname=arcname, recursive=False)
                written += 1
                if written % 50 == 0 or written == len(entries):
                    pct = 100 * written / len(entries)
                    elapsed = time.time() - t0
                    print(
                        f"  [{written:>5}/{len(entries):<5}] {pct:5.1f}%  "
                        f"{elapsed:6.1f}s elapsed  ::  {rel}",
                        flush=True,
                    )

    compressed = output_path.stat().st_size
    return len(entries), raw_total, compressed


def dry_run(source_root: Path) -> None:
    entries = collect_entries(source_root)
    raw_total = sum(f.stat().st_size for f in entries)
    print(f"Source:    {source_root}")
    print(f"Files:     {len(entries):,}")
    print(f"Raw size:  {fmt_bytes(raw_total)}")
    print()
    print("First 30 entries (sorted):")
    for f in entries[:30]:
        rel = f.relative_to(source_root)
        print(f"  {fmt_bytes(f.stat().st_size)}  {rel}")
    if len(entries) > 30:
        print(f"  ... and {len(entries) - 30:,} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compress Mini-Project/ to a single .tar.xz at max ratio."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_DIR,
        help="Directory to archive (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path. '.tar.xz' is appended if missing. "
             "(default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be archived; do not write the archive.",
    )
    args = parser.parse_args(argv)

    source: Path = args.source.resolve()
    if not source.is_dir():
        print(f"ERROR: source is not a directory: {source}", file=sys.stderr)
        return 2

    if args.dry_run:
        dry_run(source)
        return 0

    output: Path = args.output
    if output.suffix.lower() != ".xz" or not str(output).lower().endswith(".tar.xz"):
        output = output.with_name(output.name + ".tar.xz")
    output = output.resolve()

    arcname_base = source.name

    print(f"Source:    {source}")
    print(f"Output:    {output}")
    print(f"Format:    tar + xz (LZMA2, preset=9 | EXTREME, sha256)")
    print(f"Excluding: CLAUDE.md, .DS_Store, build aux, __pycache__, .agents, SUBMISSION/, ...")
    print()
    t0 = time.time()
    n, raw, comp = build_archive(source, output, arcname_base)
    dt = time.time() - t0

    ratio = (1 - comp / raw) * 100 if raw else 0.0
    print()
    print("Done.")
    print(f"  Files archived:   {n:,}")
    print(f"  Raw size:         {fmt_bytes(raw)}")
    print(f"  Compressed size:  {fmt_bytes(comp)}")
    print(f"  Saved:            {ratio:5.2f}%")
    print(f"  Elapsed:          {dt:7.1f}s")
    print(f"  Archive:          {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
