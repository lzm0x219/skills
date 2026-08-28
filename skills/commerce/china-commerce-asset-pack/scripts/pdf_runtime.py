"""PDF renderer seam with structured results and isolated adapters."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import NamedTuple

from browser_runtime import is_pdf_file, render_pdf_with_browser


WEASYPRINT_RENDER_TIMEOUT_SECONDS = 60
WEASYPRINT_RUNNER = Path(__file__).with_name("weasyprint_runner.py")


class RenderRequest(NamedTuple):
    engine: str
    html_path: Path
    output_path: Path
    resource_root: Path
    browser: Path | None = None


class RenderResult(NamedTuple):
    success: bool
    engine: str
    error_kind: str = ""
    message: str = ""


def _render_with_chrome(request: RenderRequest, timeout: float) -> RenderResult:
    if request.browser is None:
        return RenderResult(False, "chrome", "unavailable", "Chrome/Chromium was not found")
    success, error = render_pdf_with_browser(
        request.browser,
        request.html_path,
        request.output_path,
        timeout=timeout,
    )
    if not success:
        return RenderResult(False, "chrome", "render_failed", error)
    return RenderResult(True, "chrome")


def _render_with_weasyprint(request: RenderRequest, timeout: float) -> RenderResult:
    request.output_path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="china-commerce-asset-pack-weasy-") as runtime_home:
        environment = os.environ.copy()
        for variable in ("PYTHONHOME", "PYTHONINSPECT", "PYTHONPATH"):
            environment.pop(variable, None)
        environment.update(
            {
                "HOME": runtime_home,
                "XDG_CACHE_HOME": str(Path(runtime_home) / "cache"),
                "XDG_CONFIG_HOME": str(Path(runtime_home) / "config"),
            }
        )
        command = [
            sys.executable,
            str(WEASYPRINT_RUNNER),
            str(request.html_path),
            str(request.output_path),
            str(request.resource_root),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=environment,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            request.output_path.unlink(missing_ok=True)
            return RenderResult(False, "weasyprint", "timeout", "WeasyPrint timed out")
        except OSError as error:
            request.output_path.unlink(missing_ok=True)
            return RenderResult(False, "weasyprint", "unavailable", str(error))

    if result.returncode != 0:
        request.output_path.unlink(missing_ok=True)
        message = result.stderr.strip() or result.stdout.strip() or "WeasyPrint failed"
        return RenderResult(False, "weasyprint", "render_failed", message)
    if not is_pdf_file(request.output_path):
        request.output_path.unlink(missing_ok=True)
        return RenderResult(
            False,
            "weasyprint",
            "invalid_output",
            "WeasyPrint did not create a valid PDF",
        )
    return RenderResult(True, "weasyprint")


def render_pdf(
    request: RenderRequest,
    *,
    timeout: float = WEASYPRINT_RENDER_TIMEOUT_SECONDS,
) -> RenderResult:
    """Render one request through the selected adapter without fallback or logging."""
    if request.engine == "chrome":
        return _render_with_chrome(request, timeout)
    if request.engine == "weasyprint":
        return _render_with_weasyprint(request, timeout)
    raise ValueError(f"unsupported PDF engine: {request.engine}")
