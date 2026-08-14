#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any

from bootstrap_zig import (
    ASSETS_DIR,
    BootstrapFailure,
    render_text,
    run_command,
    write_report,
)


VERSION_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
ZIG_VERSION_PATTERN = re.compile(
    r'\.minimum_zig_version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"'
)
TASK_SECTION_PATTERN = re.compile(
    r"(?ms)^\[tasks\.([A-Za-z0-9_-]+)\]\n.*?(?=^\[|\Z)"
)
IGNORED_MANIFEST_ROOTS = {".git", ".zig-cache", "zig-out"}
PRESERVED_PROJECT_PATHS = {
    "README.md",
    "build.zig",
    "build.zig.zon",
    "src/root.zig",
}
ALTERNATIVE_PATHS = {
    ".husky": "Husky",
    ".pre-commit-config.yaml": "pre-commit",
    ".pre-commit-config.yml": "pre-commit",
    ".tool-versions": "asdf",
}
LEGACY_LEFTHOOK = """pre-commit:
  parallel: true
  commands:
    fmt:
      glob: "*.zig"
      run: mise exec -- zig fmt {staged_files}
      stage_fixed: true
    test:
      run: mise exec -- zig build test
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Complete the development baseline of a supported existing Zig library "
            "without replacing business source or unknown configuration."
        )
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--mise", default="mise", metavar="COMMAND")
    parser.add_argument("--git", default="git", metavar="COMMAND")
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def normalized_text(source: str) -> str:
    return "\n".join(line.rstrip() for line in source.strip().splitlines()) + "\n"


def read_regular_file(target: Path, relative: str) -> str:
    path = target / relative
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure(
            f"required regular file is missing: {relative}",
            status="blocked",
        )
    return path.read_text(encoding="utf-8")


def sanitized_git_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def probe_git(target: Path, git: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [git, "-C", str(target), *args],
            capture_output=True,
            text=True,
            check=False,
            env=sanitized_git_environment(),
        )
    except OSError as error:
        raise BootstrapFailure(
            f"unable to inspect Git with {git!r}: {error}",
            status="blocked",
        ) from error


def file_manifest(target: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        relative = path.relative_to(target)
        if relative.parts and relative.parts[0] in IGNORED_MANIFEST_ROOTS:
            continue
        if path.is_symlink():
            manifest[relative.as_posix()] = "symlink:" + os.readlink(path)
        elif path.is_file():
            manifest[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def split_changes(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, list[str]]:
    before_paths = set(before)
    after_paths = set(after)
    return {
        "created": sorted(after_paths - before_paths),
        "modified": sorted(
            path
            for path in before_paths & after_paths
            if before[path] != after[path]
        ),
        "deleted": sorted(before_paths - after_paths),
    }


def add_conflict(report: dict[str, Any], message: str) -> None:
    report["conflicts"].append(message)


def inspect_alternatives(target: Path, report: dict[str, Any]) -> None:
    for relative, tool in sorted(ALTERNATIVE_PATHS.items()):
        if (target / relative).exists() or (target / relative).is_symlink():
            add_conflict(report, f"{relative} indicates {tool}; confirm migration first")
    package_json = target / "package.json"
    if package_json.is_file():
        try:
            package_data = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            add_conflict(report, "package.json is not safely inspectable")
        else:
            if "volta" in package_data:
                add_conflict(
                    report,
                    "package.json contains Volta configuration; confirm migration first",
                )


def inspect_git(target: Path, options: argparse.Namespace, report: dict[str, Any]) -> None:
    git_metadata = target / ".git"
    if git_metadata.is_symlink() or not git_metadata.is_dir():
        add_conflict(
            report,
            "linked worktrees and non-directory .git metadata are outside this slice",
        )
    repository = probe_git(target, options.git, ["rev-parse", "--show-toplevel"])
    if repository.returncode != 0:
        add_conflict(report, "target is not an existing Git repository")
        return
    if Path(repository.stdout.strip()).resolve() != target.resolve():
        add_conflict(report, "target must be the exact Git repository root")

    hooks_path = probe_git(target, options.git, ["config", "--get", "core.hooksPath"])
    configured_hooks = hooks_path.stdout.strip() if hooks_path.returncode == 0 else ""
    if configured_hooks not in ("", ".git/hooks"):
        add_conflict(
            report,
            f"core.hooksPath={configured_hooks!r} requires explicit migration approval",
        )
    pre_commit = target / ".git" / "hooks" / "pre-commit"
    if pre_commit.is_file():
        source = pre_commit.read_text(encoding="utf-8", errors="replace")
        if "LEFTHOOK" not in source.upper():
            add_conflict(
                report,
                ".git/hooks/pre-commit is not a recognized Lefthook entry",
            )


def inspect_versions(
    target: Path,
    report: dict[str, Any],
) -> tuple[str, str, dict[str, Any], str]:
    mise_source = read_regular_file(target, "mise.toml")
    zon_source = read_regular_file(target, "build.zig.zon")
    try:
        mise_data = tomllib.loads(mise_source)
    except tomllib.TOMLDecodeError as error:
        raise BootstrapFailure(
            f"mise.toml is not valid TOML: {error}",
            status="blocked",
        ) from error

    unknown_tables = sorted(
        set(mise_data) - {"hooks", "settings", "tasks", "tools"}
    )
    if unknown_tables:
        raise BootstrapFailure(
            "mise.toml contains unsupported top-level data: "
            + ", ".join(unknown_tables),
            status="blocked",
        )
    tools = mise_data.get("tools")
    if not isinstance(tools, dict):
        raise BootstrapFailure("mise.toml must contain [tools]", status="blocked")
    zig_version = tools.get("zig")
    lefthook_version = tools.get("lefthook")
    unknown_tools = sorted(set(tools) - {"zig", "lefthook"})
    if unknown_tools:
        raise BootstrapFailure(
            "mise.toml contains additional tools that would be installed: "
            + ", ".join(unknown_tools),
            status="blocked",
        )
    hooks = mise_data.get("hooks", {})
    if not isinstance(hooks, dict) or set(hooks) - {"postinstall"}:
        raise BootstrapFailure(
            "mise.toml contains unsupported hooks",
            status="blocked",
        )
    postinstall = hooks.get("postinstall")
    if postinstall not in (None, "lefthook install", "lefthook install --force"):
        raise BootstrapFailure(
            "mise.toml postinstall hook is not recognized",
            status="blocked",
        )
    if not isinstance(zig_version, str) or not VERSION_PATTERN.fullmatch(zig_version):
        raise BootstrapFailure(
            "mise.toml must pin Zig to an exact x.y.z version",
            status="blocked",
        )
    if not isinstance(lefthook_version, str) or not VERSION_PATTERN.fullmatch(
        lefthook_version
    ):
        raise BootstrapFailure(
            "mise.toml must pin Lefthook to an exact x.y.z version",
            status="blocked",
        )
    zon_match = ZIG_VERSION_PATTERN.search(zon_source)
    if zon_match is None:
        raise BootstrapFailure(
            "build.zig.zon must declare an exact minimum_zig_version",
            status="blocked",
        )
    if zon_match.group(1) != zig_version:
        raise BootstrapFailure(
            "Zig version conflict between mise.toml and build.zig.zon",
            status="blocked",
        )
    report["versions"] = {"zig": zig_version, "lefthook": lefthook_version}
    return zig_version, lefthook_version, mise_data, mise_source


def inspect_lockfile(
    target: Path,
    zig_version: str,
    lefthook_version: str,
) -> None:
    lock_path = target / "mise.lock"
    if not lock_path.exists():
        return
    if lock_path.is_symlink() or not lock_path.is_file():
        raise BootstrapFailure("mise.lock is not a regular file", status="blocked")
    try:
        lock_data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BootstrapFailure(
            f"mise.lock is not valid TOML: {error}",
            status="blocked",
        ) from error
    tools = lock_data.get("tools", {})
    if not isinstance(tools, dict):
        raise BootstrapFailure("mise.lock tools are not inspectable", status="blocked")
    for tool, expected in (("zig", zig_version), ("lefthook", lefthook_version)):
        entries = tools.get(tool, [])
        if isinstance(entries, dict):
            entries = [entries]
        if entries and any(
            not isinstance(entry, dict) or entry.get("version") != expected
            for entry in entries
        ):
            raise BootstrapFailure(
                f"{tool} version conflict between mise.toml and mise.lock",
                status="blocked",
            )


def merge_settings(source: str, data: dict[str, Any]) -> str:
    settings = data.get("settings")
    if settings is None:
        return source.rstrip() + "\n\n[settings]\nlockfile = true\n"
    if not isinstance(settings, dict):
        raise BootstrapFailure("[settings] is not safely mergeable", status="blocked")
    lockfile = settings.get("lockfile")
    if lockfile is False:
        raise BootstrapFailure(
            "mise lockfile is explicitly disabled",
            status="blocked",
        )
    if lockfile is True:
        return source
    section = re.search(r"(?m)^\[settings\]\s*$", source)
    if section is None:
        raise BootstrapFailure(
            "existing mise settings use an unsupported structure",
            status="blocked",
        )
    next_section = re.search(r"(?m)^\[", source[section.end() :])
    insertion = (
        section.end() + next_section.start() if next_section is not None else len(source)
    )
    prefix = source[:insertion].rstrip()
    suffix = source[insertion:].lstrip("\n")
    return prefix + "\nlockfile = true\n\n" + suffix


def merge_tasks(source: str, data: dict[str, Any]) -> str:
    asset = (ASSETS_DIR / "existing" / "mise-tasks.toml.tmpl").read_text(
        encoding="utf-8"
    )
    expected = tomllib.loads(asset)["tasks"]
    existing = data.get("tasks", {})
    if not isinstance(existing, dict):
        raise BootstrapFailure("[tasks] is not safely mergeable", status="blocked")
    sections = {
        match.group(1): match.group(0).rstrip()
        for match in TASK_SECTION_PATTERN.finditer(asset)
    }
    additions: list[str] = []
    for name, expected_task in expected.items():
        current = existing.get(name)
        if current is None:
            additions.append(sections[name])
            continue
        if (
            not isinstance(current, dict)
            or set(current) - {"description", "run"}
            or current.get("run") != expected_task.get("run")
        ):
            raise BootstrapFailure(
                f"existing mise task {name!r} has unknown behavior",
                status="blocked",
            )
    if not additions:
        return source
    return source.rstrip() + "\n\n" + "\n\n".join(additions) + "\n"


def desired_asset(relative: str, values: dict[str, str]) -> str:
    source = (ASSETS_DIR / "common" / relative).read_text(encoding="utf-8")
    return render_text(source, values)


def plan_files(
    target: Path,
    mise_data: dict[str, Any],
    mise_source: str,
    values: dict[str, str],
    report: dict[str, Any],
) -> dict[str, str]:
    build_source = read_regular_file(target, "build.zig")
    read_regular_file(target, "src/root.zig")
    if "b.addRunArtifact" not in build_source or 'b.step("test"' not in build_source:
        add_conflict(report, "build.zig does not prove that its test step executes tests")

    merged_mise = merge_tasks(merge_settings(mise_source, mise_data), mise_data)
    desired_lefthook = desired_asset("lefthook.yml.tmpl", values)
    current_lefthook = read_regular_file(target, "lefthook.yml")
    normalized_current = normalized_text(current_lefthook)
    if normalized_current not in (
        normalized_text(LEGACY_LEFTHOOK),
        normalized_text(desired_lefthook),
    ):
        add_conflict(report, "lefthook.yml contains unknown behavior")

    planned = {
        "mise.toml": merged_mise,
        "lefthook.yml": desired_lefthook,
        ".lefthook/partial-stage-guard.sh": desired_asset(
            ".lefthook/partial-stage-guard.sh.tmpl",
            values,
        ),
        ".github/workflows/validate.yml": desired_asset(
            ".github/workflows/validate.yml.tmpl",
            values,
        ),
        ".github/renovate.json": desired_asset(
            ".github/renovate.json.tmpl",
            values,
        ),
    }
    for relative, desired in planned.items():
        path = target / relative
        if path.is_symlink():
            add_conflict(report, f"{relative} is a symlink")
        elif path.exists() and not path.is_file():
            add_conflict(report, f"{relative} is not a regular file")
        elif path.is_file() and relative not in ("mise.toml", "lefthook.yml"):
            if path.read_text(encoding="utf-8") != desired:
                add_conflict(report, f"{relative} contains unknown content")
    return planned


def write_planned_files(target: Path, planned: dict[str, str]) -> None:
    for relative, source in planned.items():
        path = target / relative
        if path.is_file() and path.read_text(encoding="utf-8") == source:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    (target / ".lefthook" / "partial-stage-guard.sh").chmod(0o755)
    (target / "mise.lock").touch(exist_ok=True)


def verify_hook(target: Path, options: argparse.Namespace) -> None:
    hook_path = target / ".git" / "hooks" / "pre-commit"
    if not hook_path.is_file() or not os.access(hook_path, os.X_OK):
        raise BootstrapFailure(
            "Lefthook returned success but did not install an executable pre-commit hook",
            status="partial",
            failed_command=[
                options.mise,
                "exec",
                "--",
                "lefthook",
                "install",
                "--force",
            ],
        )


def apply_baseline(options: argparse.Namespace, report: dict[str, Any]) -> None:
    requested_target = options.target.expanduser().absolute()
    if requested_target.is_symlink() or not requested_target.is_dir():
        raise BootstrapFailure(
            "target must be an existing non-symlink directory",
            status="blocked",
        )
    target = requested_target.resolve()
    report["target"] = str(target)
    before = file_manifest(target)
    report["_before_manifest"] = before

    inspect_alternatives(target, report)
    inspect_git(target, options, report)
    zig_version, lefthook_version, mise_data, mise_source = inspect_versions(
        target,
        report,
    )
    inspect_lockfile(target, zig_version, lefthook_version)
    values = {
        "LEFTHOOK_VERSION": lefthook_version,
        "PROJECT_NAME": "existing",
        "PROJECT_SHAPE": "library",
        "ZIG_VERSION": zig_version,
    }
    planned = plan_files(target, mise_data, mise_source, values, report)
    if report["conflicts"]:
        raise BootstrapFailure(
            "existing project has conflicts that require confirmation",
            status="blocked",
        )

    write_planned_files(target, planned)
    commands: list[dict[str, object]] = report["commands"]
    mise_environment = {"MISE_TRUSTED_CONFIG_PATHS": str(target)}
    run_command(
        [options.mise, "install"],
        target,
        commands,
        env_overrides=mise_environment,
        sanitize_git=True,
    )
    run_command(
        [options.mise, "exec", "--", "lefthook", "install", "--force"],
        target,
        commands,
        env_overrides=mise_environment,
        sanitize_git=True,
    )
    verify_hook(target, options)
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

    after = file_manifest(target)
    changes = split_changes(before, after)
    allowed = set(planned) | {"mise.lock"}
    unexpected = sorted(
        (set(changes["created"]) | set(changes["modified"]) | set(changes["deleted"]))
        - allowed
    )
    if unexpected:
        raise BootstrapFailure(
            "unexpected project mutations: " + ", ".join(unexpected),
            status="partial",
        )
    for relative in PRESERVED_PROJECT_PATHS:
        if before.get(relative) != after.get(relative):
            raise BootstrapFailure(
                f"preserved project file changed: {relative}",
                status="partial",
            )
    report["changes"] = changes
    report["verification"]["preserved_project_files"] = "passed"
    report["status"] = "completed"
    report.pop("_before_manifest", None)


def main() -> int:
    options = parse_args()
    target = options.target.expanduser().absolute().resolve(strict=False)
    report_path = options.report.expanduser().absolute().resolve(strict=False)
    if report_path == target or target in report_path.parents:
        print("--report must be outside the target directory", file=sys.stderr)
        return 2
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "existing",
        "stack": "zig",
        "shape": "library",
        "status": "blocked",
        "target": str(target),
        "versions": {},
        "changes": {"created": [], "modified": [], "deleted": []},
        "conflicts": [],
        "commands": [],
        "failed_command": None,
        "error": None,
        "recovery": None,
        "verification": {
            "lefthook": "not-run",
            "mise_run_ci": "not-run",
            "preserved_project_files": "not-run",
        },
    }
    try:
        apply_baseline(options, report)
    except BootstrapFailure as error:
        report["status"] = error.status
        report["failed_command"] = error.failed_command
        report["error"] = str(error)
        if error.status == "partial":
            report["recovery"] = (
                "Inspect the recorded command output and partial changes, correct "
                "the failure, then rerun the exact failed command or the adapter."
            )
            if report["verification"]["mise_run_ci"] == "running":
                report["verification"]["mise_run_ci"] = "failed"
        else:
            report["recovery"] = (
                "Resolve each reported conflict explicitly, then rerun inventory."
            )
        before = report.pop("_before_manifest", None)
        target_path = Path(report["target"])
        if isinstance(before, dict) and target_path.is_dir():
            after = file_manifest(target_path)
            report["changes"] = split_changes(before, after)
            if all(
                before.get(relative) == after.get(relative)
                for relative in PRESERVED_PROJECT_PATHS
            ):
                report["verification"]["preserved_project_files"] = "passed"
        write_report(options.report, report)
        print(str(error), file=sys.stderr)
        return 1
    write_report(options.report, report)
    print(f"completed existing Zig baseline at {report['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
