#!/usr/bin/env python3
"""Discover and probe a local Chromium-family browser."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


BROWSER_COMMANDS = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "msedge",
)

MACOS_BROWSER_PATHS = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
)

WINDOWS_BROWSER_SUFFIXES = (
    Path("Google/Chrome/Application/chrome.exe"),
    Path("Chromium/Application/chrome.exe"),
    Path("Microsoft/Edge/Application/msedge.exe"),
)

CHROME_RENDER_TIMEOUT_SECONDS = 60
CHROME_RENDER_FLAGS = (
    "--headless",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-gpu",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-first-run",
    "--no-pdf-header-footer",
    "--safebrowsing-disable-auto-update",
    "--incognito",
)


def is_pdf_file(path: Path) -> bool:
    """Return whether ``path`` has a nontrivial PDF envelope."""
    try:
        with path.open("rb") as stream:
            size = path.stat().st_size
            if size < 64 or not re.fullmatch(rb"%PDF-\d\.\d", stream.read(8)):
                return False
            stream.seek(max(0, size - 1024))
            tail = stream.read()
            marker, separator, trailing = tail.rpartition(b"%%EOF")
            return bool(marker and separator and not trailing.strip())
    except OSError:
        return False


def browser_render_flags() -> tuple[str, ...]:
    """Return non-interactive flags for the current operating system."""
    if sys.platform == "darwin":
        return (*CHROME_RENDER_FLAGS, "--use-mock-keychain")
    if sys.platform.startswith("linux"):
        return (*CHROME_RENDER_FLAGS, "--password-store=basic")
    return CHROME_RENDER_FLAGS


def find_browser(explicit: Path | None = None) -> Path | None:
    """Return a detected browser executable without claiming it is usable."""
    if explicit:
        resolved = explicit.expanduser()
        return resolved if resolved.is_file() else None

    env_path = os.environ.get("CHINA_COMMERCE_ASSET_PACK_CHROME", "").strip()
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.is_file():
            return candidate

    for command in BROWSER_COMMANDS:
        resolved = shutil.which(command)
        if resolved:
            return Path(resolved)

    for path in MACOS_BROWSER_PATHS:
        if path.is_file():
            return path

    windows_roots = (
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    )
    for root in filter(None, windows_roots):
        for suffix in WINDOWS_BROWSER_SUFFIXES:
            candidate = Path(root) / suffix
            if candidate.is_file():
                return candidate
    return None


def render_pdf_with_browser(
    browser: Path,
    html_path: Path,
    output_path: Path,
    *,
    timeout: float = CHROME_RENDER_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    """Render one local HTML file with the isolated production browser flags."""
    with tempfile.TemporaryDirectory(prefix="china-commerce-asset-pack-chrome-") as profile:
        render_environment = os.environ.copy()
        render_environment.update(
            {
                "HOME": profile,
                "LOCALAPPDATA": profile,
                "USERPROFILE": profile,
                "XDG_CACHE_HOME": str(Path(profile) / "cache"),
                "XDG_CONFIG_HOME": str(Path(profile) / "config"),
            }
        )
        command = [
            str(browser),
            *browser_render_flags(),
            f"--print-to-pdf={output_path}",
            html_path.resolve().as_uri(),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=render_environment,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, str(error)

    if result.returncode != 0:
        return False, result.stderr.strip()
    if not is_pdf_file(output_path):
        return False, "browser did not create a valid PDF"
    return True, ""


def browser_usable(browser: Path, timeout: float = 15) -> bool:
    """Verify that the browser can render a minimal local HTML file to PDF."""
    with tempfile.TemporaryDirectory(prefix="china-commerce-asset-pack-browser-probe-") as directory:
        probe_root = Path(directory)
        html_path = probe_root / "probe.html"
        output_path = probe_root / "probe.pdf"
        html_path.write_text("<!doctype html><meta charset=utf-8><p>PDF probe</p>", encoding="utf-8")
        usable, _error = render_pdf_with_browser(
            browser,
            html_path,
            output_path,
            timeout=timeout,
        )
        return usable
