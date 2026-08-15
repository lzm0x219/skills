#!/usr/bin/env python3
"""Normalize a folder of raster pages to one exact size without stretching."""

from __future__ import annotations

import argparse
from collections import Counter
import sys
from pathlib import Path
import tempfile
import warnings

from atomic_output import OutputExistsError, commit_staged_files


EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_INPUT_PIXELS = 50_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Center-crop and scale product-detail pages to an exact size."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1440)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing existing PNG files in the output directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.width <= 0 or args.height <= 0 or args.width > 32768 or args.height > 32768:
        raise SystemExit("width and height must be between 1 and 32768")
    if not args.input_dir.is_dir():
        raise SystemExit(f"input directory not found: {args.input_dir}")

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if input_dir == output_dir:
        raise SystemExit("input and output directories must be different")

    files = sorted(
        path for path in args.input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    )
    if not files:
        raise SystemExit(f"no supported images found in: {args.input_dir}")

    destinations = [args.output_dir / f"{source.stem}.png" for source in files]
    destination_counts = Counter(path.name.casefold() for path in destinations)
    duplicate_names = sorted(
        {path.name for path in destinations if destination_counts[path.name.casefold()] > 1},
        key=str.casefold,
    )
    if duplicate_names:
        preview = ", ".join(duplicate_names[:5])
        suffix = "..." if len(duplicate_names) > 5 else ""
        raise SystemExit(
            f"multiple source images map to the same output: {preview}{suffix}; "
            "rename the source files before converting"
        )
    existing = [path for path in destinations if path.exists()]
    if existing and not args.overwrite:
        preview = ", ".join(path.name for path in existing[:5])
        suffix = "..." if len(existing) > 5 else ""
        raise SystemExit(
            f"output files already exist: {preview}{suffix}; pass --overwrite to replace them"
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ModuleNotFoundError:
        print("Pillow is required but is not installed", file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory(
            prefix=".normalize-images-",
            dir=args.output_dir,
        ) as staging_directory:
            staging_root = Path(staging_directory)
            staged_files: list[tuple[Path, Path]] = []
            for source, destination in zip(files, destinations):
                staged_path = staging_root / destination.name
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(source) as image:
                        if image.width * image.height > MAX_INPUT_PIXELS:
                            raise ValueError(f"image is too large: {source.name}")
                        transposed = ImageOps.exif_transpose(image)
                        mode = (
                            "RGBA"
                            if transposed.mode in {"LA", "RGBA"}
                            or "transparency" in transposed.info
                            else "RGB"
                        )
                        normalized = ImageOps.fit(
                            transposed.convert(mode),
                            (args.width, args.height),
                            method=Image.Resampling.LANCZOS,
                            centering=(0.5, 0.5),
                        )
                        normalized.save(staged_path, format="PNG", optimize=True)
                staged_files.append((staged_path, destination))
            commit_staged_files(staged_files, overwrite=args.overwrite)
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        OutputExistsError,
        UnidentifiedImageError,
        ValueError,
    ) as error:
        print(f"image normalization failed: {error}", file=sys.stderr)
        return 1

    for destination in destinations:
        print(destination)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
