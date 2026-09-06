#!/usr/bin/env python3

from __future__ import annotations

import argparse
import binascii
import math
from pathlib import Path
import re
import struct
import sys

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TARGET_ASPECT_RATIO = 16 / 9
REQUIRED_SOURCE_FACT_FIELDS = (
    "core_claim",
    "exact_terms",
    "required_relationships",
    "required_counts",
    "unsupported_inferences",
    "script",
    "allowed_labels",
)
REQUIRED_RECORD_SECTIONS = (
    "来源锚点",
    "来源事实卡",
    "最终提示词",
    "参考与工具",
    "QA",
    "迭代记录",
    "最终输出",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Juanjuan PNG and its same-name prompt record."
    )
    parser.add_argument("image", type=Path, help="path to the generated PNG")
    parser.add_argument(
        "--record",
        type=Path,
        help="prompt record path; defaults to <image-stem>.prompt.md",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="maximum relative aspect-ratio error (default: 0.01)",
    )
    args = parser.parse_args()
    if not math.isfinite(args.tolerance) or args.tolerance < 0:
        parser.error("--tolerance must be finite and non-negative")
    return args


def png_dimensions(path: Path) -> tuple[int, int]:
    """Check chunk framing and CRCs; pixel decoding remains a separate check."""
    with path.open("rb") as image_file:
        if image_file.read(8) != PNG_SIGNATURE:
            raise ValueError("not a PNG signature")
        dimensions = None
        idat_bytes = 0
        idat_ended = False
        while True:
            chunk_header = image_file.read(8)
            if len(chunk_header) != 8:
                raise ValueError("truncated PNG or missing IEND")
            length, kind = struct.unpack(">I4s", chunk_header)
            if length > 0x7FFFFFFF:
                raise ValueError("invalid PNG chunk length")
            if dimensions is None and (kind != b"IHDR" or length != 13):
                raise ValueError("PNG must begin with a 13-byte IHDR")
            if dimensions is not None and kind == b"IHDR":
                raise ValueError("duplicate PNG IHDR")
            checksum = binascii.crc32(kind)
            remaining = length
            header = b""
            while remaining:
                # Do not allocate from an untrusted chunk length.
                data = image_file.read(min(remaining, 65536))
                if not data:
                    raise ValueError("truncated PNG chunk")
                checksum = binascii.crc32(data, checksum)
                remaining -= len(data)
                if kind == b"IHDR":
                    header += data
            stored_crc = image_file.read(4)
            if len(stored_crc) != 4 or struct.unpack(">I", stored_crc)[0] != checksum & 0xFFFFFFFF:
                raise ValueError("invalid PNG chunk CRC")
            if kind == b"IHDR":
                width, height, depth, color, compression, filtering, interlace = struct.unpack(
                    ">IIBBBBB", header
                )
                depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
                if not (0 < width <= 0x7FFFFFFF and 0 < height <= 0x7FFFFFFF):
                    raise ValueError("PNG dimensions must be positive 31-bit integers")
                if depth not in depths.get(color, ()) or compression != 0 or filtering != 0 or interlace not in (0, 1):
                    raise ValueError("invalid PNG IHDR fields")
                dimensions = (width, height)
            elif kind == b"IDAT":
                if idat_ended:
                    raise ValueError("PNG IDAT chunks must be consecutive")
                idat_bytes += length
            elif kind == b"IEND":
                if length or not idat_bytes or image_file.read(1):
                    raise ValueError("PNG requires image data and a final empty IEND")
                return dimensions
            elif idat_bytes:
                idat_ended = True


def markdown_section(record: str, title: str) -> str | None:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(title)}\s*$\s*(.*?)(?=^##\s|\Z)",
        record,
    )
    return match.group(1) if match is not None else None


def validate_prompt_record(record_path: Path, image_path: Path) -> list[str]:
    try:
        record = record_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"cannot read prompt record: {error}"]

    errors: list[str] = []
    sections: dict[str, str] = {}
    for section in REQUIRED_RECORD_SECTIONS:
        content = markdown_section(record, section)
        if content is None:
            errors.append(f"prompt record is missing section: {section}")
        elif not content.strip():
            errors.append(f"prompt record section is empty: {section}")
        else:
            sections[section] = content

    source_facts = sections.get("来源事实卡", "")
    for field in REQUIRED_SOURCE_FACT_FIELDS:
        pattern = rf"(?m)^\s*(?:[-*]\s*)?{re.escape(field)}\s*:\s*\S"
        if re.search(pattern, source_facts) is None:
            errors.append(f"prompt record is missing source fact field: {field}")

    qa = sections.get("QA", "")
    if re.search(r"(?mi)^\s*(?:[-*]\s*)?result\s*:\s*pass\s*$", qa) is None:
        errors.append("prompt record QA result must be pass")

    final_output_lines = {
        line.strip()
        for line in sections.get("最终输出", "").splitlines()
        if line.strip()
    }
    if str(image_path) not in final_output_lines:
        errors.append(f"prompt record final output path must include: {image_path}")
    return errors


def main() -> int:
    args = parse_args()
    image_path = args.image.resolve()
    record_path = (
        args.record.resolve()
        if args.record is not None
        else image_path.with_suffix(".prompt.md")
    )
    errors: list[str] = []

    if not image_path.is_file():
        errors.append(f"image does not exist: {image_path}")
    else:
        try:
            width, height = png_dimensions(image_path)
        except (OSError, ValueError) as error:
            errors.append(f"cannot read PNG dimensions: {error}")
        else:
            aspect_error = abs((width / height) / TARGET_ASPECT_RATIO - 1)
            if aspect_error > args.tolerance:
                errors.append(
                    f"aspect-ratio error {aspect_error:.4%} exceeds "
                    f"tolerance {args.tolerance:.4%}"
                )

    if not record_path.is_file():
        errors.append(f"prompt record does not exist: {record_path}")
    else:
        errors.extend(validate_prompt_record(record_path, image_path))

    if errors:
        print("FAIL:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"PASS: {image_path.name} is {width}x{height}; "
        f"prompt record: {record_path.name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
