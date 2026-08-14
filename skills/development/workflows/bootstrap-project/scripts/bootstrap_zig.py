#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = SKILL_DIR / "assets" / "zig"
VERSION_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
NAME_PATTERN = re.compile(r"\A[a-z][a-z0-9_]*\Z")
FINGERPRINT_PATTERN = re.compile(r"\.fingerprint\s*=\s*(0x[0-9a-fA-F]+)")
OFFICIAL_INIT_FILES = {
    "build.zig",
    "build.zig.zon",
    "src/main.zig",
    "src/root.zig",
}


class BootstrapFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: str,
        failed_command: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.failed_command = failed_command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize an empty Zig library or CLI with mise, Lefthook, CI, "
            "Renovate, and executable quality gates."
        )
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--shape", choices=("library", "cli"), required=True)
    parser.add_argument("--zig-version", required=True)
    parser.add_argument("--lefthook-version", required=True)
    parser.add_argument("--mise", default="mise", metavar="COMMAND")
    parser.add_argument("--git", default="git", metavar="COMMAND")
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def validate_options(options: argparse.Namespace) -> None:
    if not NAME_PATTERN.fullmatch(options.name):
        raise BootstrapFailure(
            "--name must start with a lowercase letter and contain only "
            "lowercase letters, digits, or underscores",
            status="blocked",
        )
    for label, value in (
        ("--zig-version", options.zig_version),
        ("--lefthook-version", options.lefthook_version),
    ):
        if not VERSION_PATTERN.fullmatch(value):
            raise BootstrapFailure(
                f"{label} must be an exact x.y.z version",
                status="blocked",
            )


def ensure_empty_target(target: Path) -> None:
    if target.is_symlink():
        raise BootstrapFailure("target cannot be a symlink", status="blocked")
    if target.exists() and not target.is_dir():
        raise BootstrapFailure("target must be a directory", status="blocked")
    if target.is_dir() and any(target.iterdir()):
        raise BootstrapFailure(
            "target must be absent or empty for new-project initialization",
            status="blocked",
        )
    target.mkdir(parents=True, exist_ok=True)


def run_command(
    argv: list[str],
    target: Path,
    commands: list[dict[str, object]],
    *,
    env_overrides: dict[str, str] | None = None,
    sanitize_git: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    removed_environment: list[str] = []
    if sanitize_git:
        removed_environment = sorted(key for key in environment if key.startswith("GIT_"))
        for key in removed_environment:
            environment.pop(key)
    if env_overrides:
        environment.update(env_overrides)
    try:
        completed = subprocess.run(
            argv,
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
    except OSError as error:
        commands.append(
            {
                "argv": argv,
                "cwd": str(target),
                "returncode": None,
                "environment": env_overrides or {},
                "environment_removed": removed_environment,
                "stdout": "",
                "stderr": str(error),
            }
        )
        raise BootstrapFailure(
            f"unable to run {argv[0]!r}: {error}",
            status="partial",
            failed_command=argv,
        ) from error
    commands.append(
        {
            "argv": argv,
            "cwd": str(target),
            "returncode": completed.returncode,
            "environment": env_overrides or {},
            "environment_removed": removed_environment,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    )
    if completed.returncode != 0:
        raise BootstrapFailure(
            f"command exited with status {completed.returncode}: {' '.join(argv)}",
            status="partial",
            failed_command=argv,
        )
    return completed


def project_files(
    target: Path,
    *,
    ignored_roots: set[str] | None = None,
) -> set[str]:
    ignored = ignored_roots or {".git"}
    files: set[str] = set()
    for path in target.rglob("*"):
        relative = path.relative_to(target)
        if relative.parts and relative.parts[0] in ignored:
            continue
        if path.is_file() or path.is_symlink():
            files.add(relative.as_posix())
    return files


def render_text(source: str, values: dict[str, str]) -> str:
    rendered = source
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    unresolved = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", rendered)))
    if unresolved:
        raise BootstrapFailure(
            f"unresolved template values: {', '.join(unresolved)}",
            status="partial",
        )
    return rendered


def render_tree(source_root: Path, target: Path, values: dict[str, str]) -> None:
    for source_path in sorted(source_root.rglob("*")):
        if not source_path.is_file():
            continue
        relative = source_path.relative_to(source_root)
        output_name = relative.name.removesuffix(".tmpl")
        output_path = target / relative.with_name(output_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        source = source_path.read_text(encoding="utf-8")
        output_path.write_text(render_text(source, values), encoding="utf-8")


def remove_generated_file(path: Path) -> None:
    if path.exists():
        if not path.is_file() or path.is_symlink():
            raise BootstrapFailure(
                f"expected an official initializer file: {path}",
                status="partial",
            )
        path.unlink()


def initialize(options: argparse.Namespace, report: dict[str, Any]) -> None:
    validate_options(options)
    requested_target = options.target.expanduser().absolute()
    ensure_empty_target(requested_target)
    target = requested_target.resolve()
    report["target"] = str(target)
    commands: list[dict[str, object]] = report["commands"]

    run_command([options.git, "init"], target, commands, sanitize_git=True)
    run_command(
        [options.git, "config", "--local", "core.hooksPath", ".git/hooks"],
        target,
        commands,
        sanitize_git=True,
    )
    values = {
        "LEFTHOOK_VERSION": options.lefthook_version,
        "PROJECT_NAME": options.name,
        "PROJECT_SHAPE": "library" if options.shape == "library" else "CLI application",
        "ZIG_VERSION": options.zig_version,
    }
    render_tree(ASSETS_DIR / "common", target, values)
    for relative in (
        ".lefthook/format-staged-zig.sh",
        ".lefthook/install-hooks.sh",
        ".lefthook/partial-stage-guard.sh",
    ):
        (target / relative).chmod(0o755)
    (target / "mise.lock").touch()
    mise_environment = {"MISE_TRUSTED_CONFIG_PATHS": str(target)}

    run_command(
        [options.mise, "install"],
        target,
        commands,
        env_overrides=mise_environment,
        sanitize_git=True,
    )
    with tempfile.TemporaryDirectory(prefix=".bootstrap-zig-init-", dir=target) as root:
        init_target = Path(root) / options.name
        init_target.mkdir()
        run_command(
            [options.mise, "exec", "--", "zig", "init"],
            init_target,
            commands,
            env_overrides=mise_environment,
            sanitize_git=True,
        )
        created_by_init = project_files(init_target)
        unexpected = sorted(created_by_init - OFFICIAL_INIT_FILES)
        missing = sorted(OFFICIAL_INIT_FILES - created_by_init)
        if unexpected or missing:
            details = []
            if unexpected:
                details.append(f"unexpected files: {', '.join(unexpected)}")
            if missing:
                details.append(f"missing files: {', '.join(missing)}")
            raise BootstrapFailure(
                "official zig init output changed; " + "; ".join(details),
                status="partial",
            )

        generated_zon = (init_target / "build.zig.zon").read_text(encoding="utf-8")
        fingerprint_match = FINGERPRINT_PATTERN.search(generated_zon)
        if fingerprint_match is None:
            raise BootstrapFailure(
                "official zig init did not produce a package fingerprint",
                status="partial",
            )
        values["PACKAGE_FINGERPRINT"] = fingerprint_match.group(1)
        for relative in sorted(OFFICIAL_INIT_FILES):
            source_path = init_target / relative
            if source_path.is_symlink() or not source_path.is_file():
                raise BootstrapFailure(
                    f"expected an official initializer file: {relative}",
                    status="partial",
                )
            output_path = target / relative
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, output_path)
    render_tree(ASSETS_DIR / "project", target, values)
    render_tree(ASSETS_DIR / options.shape, target, values)
    if options.shape == "library":
        remove_generated_file(target / "src" / "main.zig")
    else:
        remove_generated_file(target / "src" / "root.zig")
    run_command(
        [options.mise, "exec", "--", "sh", ".lefthook/install-hooks.sh"],
        target,
        commands,
        env_overrides=mise_environment,
        sanitize_git=True,
    )
    hook_path = target / ".git" / "hooks" / "pre-commit"
    safe_dispatch = (
        'export MISE_TRUSTED_CONFIG_PATHS="$(git rev-parse --show-toplevel)"; '
        'call_lefthook run "pre-commit" --no-stage-fixed "$@"'
    )
    if (
        not hook_path.is_file()
        or not os.access(hook_path, os.X_OK)
        or safe_dispatch not in hook_path.read_text(encoding="utf-8", errors="replace")
    ):
        raise BootstrapFailure(
            "Lefthook did not install the safe executable pre-commit hook",
            status="partial",
            failed_command=[
                options.mise,
                "exec",
                "--",
                "sh",
                ".lefthook/install-hooks.sh",
            ],
        )
    report["verification"]["lefthook"] = "passed"
    report["verification"]["mise_run_ci"] = "running"
    run_command(
        [options.mise, "run", "ci"],
        target,
        commands,
        env_overrides=mise_environment,
        sanitize_git=True,
    )
    report["verification"]["mise_run_ci"] = "passed"
    history = run_command(
        [options.git, "rev-list", "--all", "--count"],
        target,
        commands,
        sanitize_git=True,
    )
    if history.stdout.strip() != "0":
        raise BootstrapFailure(
            "Git history is not empty after initialization",
            status="partial",
            failed_command=[options.git, "rev-list", "--all", "--count"],
        )
    report["verification"]["no_commit"] = "passed"
    report["status"] = "completed"
    report["created"] = sorted(
        project_files(
            target,
            ignored_roots={".git", ".zig-cache", "zig-out"},
        )
    )


def write_report(path: Path, report: dict[str, Any]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    options = parse_args()
    target = options.target.expanduser().absolute().resolve(strict=False)
    report_path = options.report.expanduser().absolute().resolve(strict=False)
    if report_path == target or target in report_path.parents:
        print("--report must be outside the target directory", file=sys.stderr)
        return 2
    report: dict[str, Any] = {
        "schema_version": 1,
        "stack": "zig",
        "shape": options.shape,
        "versions": {
            "zig": options.zig_version,
            "lefthook": options.lefthook_version,
        },
        "status": "blocked",
        "commands": [],
        "created": [],
        "failed_command": None,
        "error": None,
        "recovery": None,
        "verification": {
            "lefthook": "not-run",
            "mise_run_ci": "not-run",
            "no_commit": "not-run",
        },
    }
    try:
        initialize(options, report)
    except BootstrapFailure as error:
        report["status"] = error.status
        report["failed_command"] = error.failed_command
        report["error"] = str(error)
        if error.status == "partial":
            report["recovery"] = (
                "Inspect the recorded stderr, correct the failed operation, "
                "then rerun the adapter against a fresh empty target or resume "
                "the exact failed command after reviewing the partial output."
            )
            if report["verification"]["mise_run_ci"] == "running":
                report["verification"]["mise_run_ci"] = "failed"
        else:
            report["recovery"] = "Correct the reported input conflict and rerun."
        write_report(options.report, report)
        print(str(error), file=sys.stderr)
        return 1
    write_report(options.report, report)
    print(f"completed Zig {options.shape} bootstrap at {report['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
