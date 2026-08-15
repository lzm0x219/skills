#!/usr/bin/env python3
"""Report sell-product-in-china runtime availability without installing anything."""

from __future__ import annotations

import argparse
import importlib.util
from importlib.metadata import PackageNotFoundError, version as distribution_version
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from browser_runtime import browser_usable, find_browser


def compatible_distribution(
    name: str,
    *,
    minimum: tuple[int, int, int],
    maximum: tuple[int, int, int],
) -> tuple[bool, str | None]:
    try:
        installed = distribution_version(name)
    except PackageNotFoundError:
        return False, None
    match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", installed)
    if match is None:
        return False, installed
    release = tuple(int(part or 0) for part in match.groups())
    return minimum <= release < maximum, installed


def weasyprint_usable() -> bool:
    if importlib.util.find_spec("weasyprint") is None:
        return False
    probe_code = (
        "from weasyprint import HTML; "
        "pdf = HTML(string='<p>PDF probe</p>').write_pdf(); "
        "raise SystemExit(0 if len(pdf) >= 64 and pdf.startswith(b'%PDF-') "
        "and pdf.rstrip().endswith(b'%%EOF') else 1)"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="sell-product-in-china-weasy-probe-") as directory:
            probe_environment = os.environ.copy()
            for variable in ("PYTHONHOME", "PYTHONINSPECT", "PYTHONPATH"):
                probe_environment.pop(variable, None)
            result = subprocess.run(
                [sys.executable, "-c", probe_code],
                capture_output=True,
                text=True,
                cwd=directory,
                env=probe_environment,
                timeout=30,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check sell-product-in-china dependencies without modifying the system."
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero unless PDF rendering and image normalization are ready.",
    )
    args = parser.parse_args()

    python_ok = sys.version_info >= (3, 11)
    markdown_ok, markdown_version = compatible_distribution(
        "Markdown",
        minimum=(3, 10, 2),
        maximum=(3, 11, 0),
    )
    pillow_ok, pillow_version = compatible_distribution(
        "Pillow",
        minimum=(12, 0, 0),
        maximum=(13, 0, 0),
    )
    browser = find_browser()
    browser_ok = browser_usable(browser) if browser else False
    weasy_ok = weasyprint_usable()
    pdf_ready = python_ok and markdown_ok and browser_ok
    image_normalization_ready = python_ok and pillow_ok
    overall = "ready" if pdf_ready and image_normalization_ready else "partial"

    result = {
        "status": overall,
        "python": {
            "ok": python_ok,
            "version": ".".join(map(str, sys.version_info[:3])),
            "minimum": "3.11",
        },
        "pdf": {
            "ready": pdf_ready,
            "markdown_module": markdown_ok,
            "markdown_version": markdown_version,
            "chrome": str(browser) if browser else None,
            "chrome_usable": browser_ok,
            "weasyprint_optional": weasy_ok,
        },
        "image_normalization": {
            "ready": image_normalization_ready,
            "pillow_module": pillow_ok,
            "pillow_version": pillow_version,
        },
        "optional_qa": {
            "pdfinfo": shutil.which("pdfinfo"),
            "pdftoppm": shutil.which("pdftoppm"),
            "pypdf_module": importlib.util.find_spec("pypdf") is not None,
        },
        "notes": [
            "This command only inspects the current environment; it does not install dependencies.",
            "Research and copywriting can continue when media tools are missing; report the unavailable deliverables clearly.",
        ],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"sell-product-in-china environment: {overall.upper()}")
        print(f"Python >= 3.11: {'OK' if python_ok else 'MISSING'} ({result['python']['version']})")
        print(
            f"Markdown 3.10.x: {'OK' if markdown_ok else 'MISSING/INCOMPATIBLE'} "
            f"({markdown_version or 'not found'})"
        )
        print(f"PDF renderer: {'OK' if pdf_ready else 'MISSING'}")
        browser_status = "usable" if browser_ok else "unusable"
        print(f"  Chrome/Chromium: {browser or 'not found'} ({browser_status})")
        print(f"  WeasyPrint opt-in: {'OK' if weasy_ok else 'not available'}")
        print(
            f"Image normalization (Pillow 12.x): "
            f"{'OK' if pillow_ok else 'MISSING/INCOMPATIBLE'} "
            f"({pillow_version or 'not found'})"
        )
        print("No dependencies were installed or changed.")

    if args.strict and not (pdf_ready and image_normalization_ready):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
