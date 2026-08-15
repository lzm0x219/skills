#!/usr/bin/env python3
"""Run one WeasyPrint render in a disposable subprocess."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from browser_runtime import is_pdf_file
from markdown_security import build_local_resource_fetcher, local_resource_base_uri


def apply_process_limits() -> None:
    """Bound a renderer that may parse adversarially expensive HTML/CSS."""
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows has no resource module
        return

    limits = (
        (resource.RLIMIT_CPU, 65),
        (resource.RLIMIT_FSIZE, 256 * 1024 * 1024),
        (resource.RLIMIT_NOFILE, 256),
    )
    if sys.platform.startswith("linux"):
        limits += ((resource.RLIMIT_AS, 2 * 1024 * 1024 * 1024),)
    for kind, requested in limits:
        _soft, hard = resource.getrlimit(kind)
        ceiling = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
        resource.setrlimit(kind, (ceiling, ceiling))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("resource_root", type=Path)
    args = parser.parse_args()
    try:
        apply_process_limits()
        from weasyprint import HTML

        fetcher = build_local_resource_fetcher(args.resource_root)
        HTML(
            string=args.html.read_text(encoding="utf-8"),
            base_url=local_resource_base_uri(args.resource_root),
            url_fetcher=fetcher,
        ).write_pdf(str(args.output))
    except BaseException as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        args.output.unlink(missing_ok=True)
        return 1
    return 0 if is_pdf_file(args.output) else 1


if __name__ == "__main__":
    raise SystemExit(main())
