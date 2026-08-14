#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any

from bootstrap_zig import (
    BootstrapFailure,
    SKILL_DIR,
    render_text,
    run_command,
    write_report,
)


ASSETS_DIR = SKILL_DIR / "assets" / "python"
VERSION_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
NAME_PATTERN = re.compile(r"\A[a-z0-9]+(?:[-_.][a-z0-9]+)*\Z")
REQUIRES_PYTHON_PATTERN = re.compile(r"\A(?:==|>=)([0-9]+\.[0-9]+\.[0-9]+)\Z")
IGNORED_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}
CORE_BASELINE_PATHS = {
    "mise.toml",
    "lefthook.yml",
    ".lefthook/format_staged_python.py",
    ".lefthook/install_python.py",
    ".lefthook/partial-stage-guard.sh",
    ".github/workflows/validate.yml",
    ".github/renovate.json",
}
OPTIONAL_EXISTING_PATHS = {".editorconfig", ".gitignore", "README.md"}
ALTERNATIVE_PATHS = {
    ".husky": "Husky",
    ".pre-commit-config.yaml": "pre-commit",
    ".pre-commit-config.yml": "pre-commit",
    ".tool-versions": "asdf",
    "Pipfile": "Pipenv",
    "Pipfile.lock": "Pipenv",
    "pdm.lock": "PDM",
    "poetry.lock": "Poetry",
    "setup.py": "setuptools legacy metadata",
}
DEPENDENCY_ARGUMENTS = {
    "build": "build_version",
    "mypy": "mypy_version",
    "pytest": "pytest_version",
    "ruff": "ruff_version",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new or strictly recognized existing Python package."
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--mode", choices=("new", "existing"), required=True)
    parser.add_argument("--shape", choices=("library", "cli"))
    parser.add_argument("--name")
    parser.add_argument("--python-version")
    parser.add_argument("--uv-version", required=True)
    parser.add_argument("--build-version")
    parser.add_argument("--mypy-version")
    parser.add_argument("--pytest-version")
    parser.add_argument("--ruff-version")
    parser.add_argument("--lefthook-version", required=True)
    parser.add_argument("--mise", default="mise", metavar="COMMAND")
    parser.add_argument("--git", default="git", metavar="COMMAND")
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def manifest(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        relative = path.relative_to(target)
        if any(
            part in IGNORED_NAMES or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        if path.is_symlink():
            result[relative.as_posix()] = "symlink:" + os.readlink(path)
        elif path.is_file():
            result[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def changes(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
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


def render_asset(relative: str, values: dict[str, str]) -> str:
    return render_text(
        (ASSETS_DIR / relative).read_text(encoding="utf-8"),
        values,
    )


def write_asset(target: Path, relative: str, source: str) -> None:
    path = target / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def common_assets(values: dict[str, str]) -> dict[str, str]:
    return {
        "mise.toml": render_asset("common/mise.toml.tmpl", values),
        "lefthook.yml": render_asset("common/lefthook.yml.tmpl", values),
        ".lefthook/format_staged_python.py": render_asset(
            "common/.lefthook/format_staged_python.py.tmpl",
            values,
        ),
        ".lefthook/install_python.py": render_asset(
            "common/.lefthook/install_python.py.tmpl",
            values,
        ),
        ".lefthook/partial-stage-guard.sh": render_asset(
            "common/.lefthook/partial-stage-guard.sh.tmpl",
            values,
        ),
        ".github/workflows/validate.yml": render_asset(
            "common/.github/workflows/validate.yml.tmpl",
            values,
        ),
        ".github/renovate.json": render_asset(
            "common/.github/renovate.json.tmpl",
            values,
        ),
        ".editorconfig": render_asset("common/.editorconfig.tmpl", values),
        ".gitignore": render_asset("common/.gitignore.tmpl", values),
        "README.md": render_asset("common/README.md.tmpl", values),
    }


def inspect_git_root(target: Path, git: str) -> None:
    if (target / ".git").is_symlink() or not (target / ".git").is_dir():
        raise BootstrapFailure(
            "target must use repository-local .git metadata",
            status="blocked",
        )
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    try:
        completed = subprocess.run(
            [git, "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
    except OSError as error:
        raise BootstrapFailure(
            f"unable to inspect Git with {git!r}: {error}",
            status="blocked",
        ) from error
    if completed.returncode != 0 or Path(completed.stdout.strip()).resolve() != target:
        raise BootstrapFailure(
            "target must be the exact Git repository root",
            status="blocked",
        )
    hooks_path = subprocess.run(
        [git, "-C", str(target), "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    configured_hooks = hooks_path.stdout.strip() if hooks_path.returncode == 0 else ""
    if configured_hooks not in ("", ".git/hooks"):
        raise BootstrapFailure(
            f"custom core.hooksPath={configured_hooks!r} requires confirmation",
            status="blocked",
        )
    pre_commit = target / ".git" / "hooks" / "pre-commit"
    if pre_commit.is_file():
        source = pre_commit.read_text(encoding="utf-8", errors="replace")
        if "LEFTHOOK" not in source.upper():
            raise BootstrapFailure(
                "existing pre-commit hook is not recognized as Lefthook",
                status="blocked",
            )


def inspect_alternatives(target: Path, pyproject: dict[str, Any]) -> None:
    found = [
        f"{relative} indicates {tool}"
        for relative, tool in sorted(ALTERNATIVE_PATHS.items())
        if (target / relative).exists() or (target / relative).is_symlink()
    ]
    tool = pyproject.get("tool", {})
    if isinstance(tool, dict):
        for name in ("poetry", "pdm"):
            if name in tool:
                found.append(f"pyproject.toml tool.{name} indicates {name}")
    if found:
        raise BootstrapFailure(
            "alternative project tools require migration confirmation: "
            + "; ".join(found),
            status="blocked",
        )


def load_pyproject(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure("pyproject.toml must be a regular file", status="blocked")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BootstrapFailure(
            f"pyproject.toml is invalid: {error}",
            status="blocked",
        ) from error
    if not isinstance(data, dict):
        raise BootstrapFailure("pyproject.toml must be a table", status="blocked")
    return data


def exact_version(existing: Any, requested: str | None, label: str) -> str:
    if existing is not None:
        if not isinstance(existing, str) or not VERSION_PATTERN.fullmatch(existing):
            raise BootstrapFailure(f"{label} must be an exact x.y.z version", status="blocked")
        if requested and requested != existing:
            raise BootstrapFailure(
                f"requested {label} conflicts with project metadata",
                status="blocked",
            )
        return existing
    if requested is None:
        raise BootstrapFailure(
            f"{label} is missing; provide an exact version",
            status="blocked",
        )
    return requested


def exact_requirement(requirements: list[Any], name: str) -> str | None:
    pattern = re.compile(rf"\A{re.escape(name)}==([0-9]+\.[0-9]+\.[0-9]+)\Z")
    matches = [
        match.group(1)
        for requirement in requirements
        if isinstance(requirement, str) and (match := pattern.fullmatch(requirement))
    ]
    if len(matches) > 1 and any(version != matches[0] for version in matches[1:]):
        raise BootstrapFailure(f"conflicting {name} requirements", status="blocked")
    return matches[0] if matches else None


def inspect_quality_config(
    pyproject: dict[str, Any],
    python_version: str,
) -> None:
    major, minor, _patch = python_version.split(".")
    tool = pyproject.get("tool")
    if not isinstance(tool, dict):
        raise BootstrapFailure("pyproject.toml tool configuration is missing", status="blocked")
    ruff = tool.get("ruff")
    if not isinstance(ruff, dict) or ruff.get("target-version") != f"py{major}{minor}":
        raise BootstrapFailure("Ruff target-version conflicts with Python", status="blocked")
    mypy = tool.get("mypy")
    if (
        not isinstance(mypy, dict)
        or mypy.get("python_version") != f"{major}.{minor}"
        or mypy.get("strict") is not True
    ):
        raise BootstrapFailure("mypy strict configuration is missing", status="blocked")
    pytest = tool.get("pytest")
    if not isinstance(pytest, dict) or not isinstance(pytest.get("ini_options"), dict):
        raise BootstrapFailure("pytest configuration is missing", status="blocked")


def inspect_existing(
    options: argparse.Namespace,
    target: Path,
) -> tuple[str, str, dict[str, str], str]:
    inspect_git_root(target, options.git)
    nested = [
        path
        for path in target.rglob("pyproject.toml")
        if path != target / "pyproject.toml" and ".venv" not in path.parts
    ]
    if nested:
        raise BootstrapFailure(
            "multiple pyproject.toml files require an exact subproject target",
            status="blocked",
        )
    pyproject = load_pyproject(target / "pyproject.toml")
    inspect_alternatives(target, pyproject)
    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise BootstrapFailure("pyproject.toml project table is missing", status="blocked")
    name = project.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise BootstrapFailure("Python project name is unsupported", status="blocked")
    requires_python = project.get("requires-python")
    match = (
        REQUIRES_PYTHON_PATTERN.fullmatch(requires_python)
        if isinstance(requires_python, str)
        else None
    )
    if match is None:
        raise BootstrapFailure(
            "project.requires-python must contain one exact x.y.z lower bound",
            status="blocked",
        )
    declared_python = match.group(1)
    version_path = target / ".python-version"
    if version_path.is_symlink() or not version_path.is_file():
        raise BootstrapFailure(".python-version must be a regular file", status="blocked")
    pinned_python = version_path.read_text(encoding="utf-8").strip()
    if pinned_python != declared_python:
        raise BootstrapFailure(
            ".python-version conflicts with project.requires-python",
            status="blocked",
        )
    python_version = exact_version(
        pinned_python,
        options.python_version,
        "Python",
    )
    build_system = pyproject.get("build-system")
    if not isinstance(build_system, dict) or build_system.get("build-backend") != "uv_build":
        raise BootstrapFailure("existing project must use uv_build", status="blocked")
    build_requires = build_system.get("requires")
    if not isinstance(build_requires, list):
        raise BootstrapFailure("build-system.requires must be an array", status="blocked")
    uv_build_version = exact_requirement(build_requires, "uv_build")
    exact_version(uv_build_version, options.uv_version, "uv_build")
    groups = pyproject.get("dependency-groups")
    dev = groups.get("dev") if isinstance(groups, dict) else None
    if not isinstance(dev, list):
        raise BootstrapFailure("dependency-groups.dev must be an array", status="blocked")
    dependency_versions: dict[str, str] = {}
    for dependency, argument in DEPENDENCY_ARGUMENTS.items():
        dependency_versions[dependency] = exact_version(
            exact_requirement(dev, dependency),
            getattr(options, argument),
            dependency,
        )
    inspect_quality_config(pyproject, python_version)
    module = name.replace("-", "_").replace(".", "_")
    package_root = target / "src" / module
    has_package = (package_root / "__init__.py").is_file()
    has_cli = (package_root / "cli.py").is_file()
    scripts = project.get("scripts")
    if has_cli or (isinstance(scripts, dict) and scripts):
        shape = "cli"
    elif has_package:
        shape = "library"
    else:
        raise BootstrapFailure("Python src package layout is unsupported", status="blocked")
    if not has_package or (shape == "cli" and not has_cli):
        raise BootstrapFailure("recognized Python package files are missing", status="blocked")
    tests = [path for path in (target / "tests").rglob("test_*.py") if path.is_file()]
    if not tests:
        raise BootstrapFailure("existing project requires a pytest smoke test", status="blocked")
    if options.shape and options.shape != shape:
        raise BootstrapFailure("requested shape conflicts with Python package", status="blocked")
    return name, python_version, dependency_versions, shape


def values_for(
    name: str,
    python_version: str,
    uv_version: str,
    dependency_versions: dict[str, str],
    lefthook_version: str,
    shape: str,
) -> dict[str, str]:
    major, minor, _patch = python_version.split(".")
    module = name.replace("-", "_").replace(".", "_")
    return {
        "BUILD_VERSION": dependency_versions["build"],
        "LEFTHOOK_VERSION": lefthook_version,
        "MODULE_NAME": module,
        "MYPY_VERSION": dependency_versions["mypy"],
        "PROJECT_NAME": name,
        "PROJECT_SHAPE": "library" if shape == "library" else "CLI application",
        "PYTEST_VERSION": dependency_versions["pytest"],
        "PYTHON_MAJOR_MINOR": f"{major}.{minor}",
        "PYTHON_VERSION": python_version,
        "RUFF_TARGET": f"py{major}{minor}",
        "RUFF_VERSION": dependency_versions["ruff"],
        "UV_VERSION": uv_version,
    }


def validate_versions(options: argparse.Namespace) -> None:
    fields = (
        "python_version",
        "uv_version",
        "build_version",
        "mypy_version",
        "pytest_version",
        "ruff_version",
        "lefthook_version",
    )
    for field in fields:
        value = getattr(options, field)
        if value is not None and not VERSION_PATTERN.fullmatch(value):
            flag = "--" + field.replace("_", "-")
            raise BootstrapFailure(f"{flag} must be exact x.y.z", status="blocked")


def requested_dependency_versions(options: argparse.Namespace) -> dict[str, str]:
    versions: dict[str, str] = {}
    for dependency, argument in DEPENDENCY_ARGUMENTS.items():
        value = getattr(options, argument)
        if value is None:
            raise BootstrapFailure(
                f"new mode requires --{argument.replace('_', '-')}",
                status="blocked",
            )
        versions[dependency] = value
    return versions


def plan_existing_assets(target: Path, assets: dict[str, str]) -> dict[str, str]:
    planned = {path: assets[path] for path in CORE_BASELINE_PATHS}
    for relative, desired in planned.items():
        path = target / relative
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise BootstrapFailure(f"{relative} is not safely writable", status="blocked")
        if path.is_file() and path.read_text(encoding="utf-8") != desired:
            raise BootstrapFailure(
                f"{relative} contains unknown existing content",
                status="blocked",
            )
    for relative in OPTIONAL_EXISTING_PATHS:
        path = target / relative
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise BootstrapFailure(f"{relative} is not safely writable", status="blocked")
        if not path.exists():
            planned[relative] = assets[relative]
    return planned


def inspect_mise_lock(
    target: Path,
    python_version: str,
    uv_version: str,
    lefthook_version: str,
) -> None:
    path = target / "mise.lock"
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure("mise.lock is not safely readable", status="blocked")
    if path.stat().st_size == 0:
        return
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BootstrapFailure(f"mise.lock is invalid: {error}", status="blocked") from error
    tools = data.get("tools", {})
    if not isinstance(tools, dict):
        raise BootstrapFailure("mise.lock tools are unsupported", status="blocked")
    for tool, expected in (
        ("python", python_version),
        ("uv", uv_version),
        ("lefthook", lefthook_version),
    ):
        entries = tools.get(tool, [])
        if isinstance(entries, dict):
            entries = [entries]
        if entries and any(
            not isinstance(entry, dict) or entry.get("version") != expected
            for entry in entries
        ):
            raise BootstrapFailure(
                f"{tool} version conflicts with mise.lock",
                status="blocked",
            )


def install_and_verify(
    options: argparse.Namespace,
    target: Path,
    report: dict[str, Any],
    *,
    create_lock: bool,
    install_tools: bool = True,
) -> None:
    commands: list[dict[str, object]] = report["commands"]
    environment = {
        "MISE_TRUSTED_CONFIG_PATHS": str(target),
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_NO_PROGRESS": "1",
    }
    if install_tools:
        run_command(
            [options.mise, "install"],
            target,
            commands,
            env_overrides=environment,
            sanitize_git=True,
        )
    inspect_mise_lock(
        target,
        report["versions"]["python"],
        report["versions"]["uv"],
        report["versions"]["lefthook"],
    )
    lock_command = [options.mise, "exec", "--", "uv", "lock"]
    if not create_lock:
        lock_command.append("--check")
    run_command(
        lock_command,
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    if not (target / "uv.lock").is_file():
        raise BootstrapFailure(
            "uv did not create uv.lock",
            status="partial",
            failed_command=lock_command,
        )
    report["verification"]["uv_lock"] = "passed"
    run_command(
        [options.mise, "exec", "--", "uv", "sync", "--locked", "--all-groups"],
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    run_command(
        [
            options.mise,
            "exec",
            "--",
            "python",
            ".lefthook/install_python.py",
        ],
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    hook = target / ".git" / "hooks" / "pre-commit"
    if not hook.is_file() or not os.access(hook, os.X_OK):
        raise BootstrapFailure(
            "Lefthook did not install an executable pre-commit hook",
            status="partial",
            failed_command=[
                options.mise,
                "exec",
                "--",
                "python",
                ".lefthook/install_python.py",
            ],
        )
    hook_source = hook.read_text(encoding="utf-8", errors="replace")
    if 'run "pre-commit" --no-stage-fixed' not in hook_source:
        raise BootstrapFailure(
            "installed pre-commit hook is missing the partial-stage safety flag",
            status="partial",
            failed_command=[
                options.mise,
                "exec",
                "--",
                "python",
                ".lefthook/install_python.py",
            ],
        )
    report["verification"]["lefthook"] = "passed"
    report["verification"]["mise_run_ci"] = "running"
    run_command(
        [options.mise, "run", "ci"],
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    report["verification"]["mise_run_ci"] = "passed"


def write_shape_assets(
    target: Path,
    shape: str,
    values: dict[str, str],
) -> None:
    shape_root = ASSETS_DIR / shape
    module = values["MODULE_NAME"]
    for template in shape_root.rglob("*.tmpl"):
        relative = template.relative_to(shape_root)
        parts = [module if part == "package" else part for part in relative.parts]
        destination = Path(*parts)
        destination = destination.with_name(destination.name.removesuffix(".tmpl"))
        write_asset(
            target,
            destination.as_posix(),
            render_text(template.read_text(encoding="utf-8"), values),
        )


def bootstrap_new(options: argparse.Namespace, report: dict[str, Any]) -> None:
    if not options.name or not NAME_PATTERN.fullmatch(options.name):
        raise BootstrapFailure("--name must be a lowercase Python project name", status="blocked")
    if not options.shape or not options.python_version:
        raise BootstrapFailure(
            "new mode requires --shape and --python-version",
            status="blocked",
        )
    dependency_versions = requested_dependency_versions(options)
    requested = options.target.expanduser().absolute()
    if requested.is_symlink() or (requested.exists() and not requested.is_dir()):
        raise BootstrapFailure("target must be a directory", status="blocked")
    if requested.is_dir() and any(requested.iterdir()):
        raise BootstrapFailure("new target must be absent or empty", status="blocked")
    requested.mkdir(parents=True, exist_ok=True)
    target = requested.resolve()
    report["target"] = str(target)
    report["_before"] = manifest(target)
    run_command([options.git, "init"], target, report["commands"], sanitize_git=True)
    run_command(
        [options.git, "config", "--local", "core.hooksPath", ".git/hooks"],
        target,
        report["commands"],
        sanitize_git=True,
    )
    values = values_for(
        options.name,
        options.python_version,
        options.uv_version,
        dependency_versions,
        options.lefthook_version,
        options.shape,
    )
    report["shape"] = options.shape
    report["versions"] = {
        "python": options.python_version,
        "uv": options.uv_version,
        "uv_build": options.uv_version,
        "build": dependency_versions["build"],
        "mypy": dependency_versions["mypy"],
        "pytest": dependency_versions["pytest"],
        "ruff": dependency_versions["ruff"],
        "lefthook": options.lefthook_version,
    }
    for relative, source in common_assets(values).items():
        write_asset(target, relative, source)
    (target / ".lefthook" / "partial-stage-guard.sh").chmod(0o755)
    (target / "mise.lock").touch()
    environment = {
        "MISE_TRUSTED_CONFIG_PATHS": str(target),
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_NO_PROGRESS": "1",
    }
    run_command(
        [options.mise, "install"],
        target,
        report["commands"],
        env_overrides=environment,
        sanitize_git=True,
    )
    before_init = manifest(target)
    init_arguments = ["--lib"] if options.shape == "library" else ["--package", "--app"]
    run_command(
        [
            options.mise,
            "exec",
            "--",
            "uv",
            "init",
            *init_arguments,
            "--build-backend",
            "uv",
            "--vcs",
            "none",
            "--no-workspace",
            "--author-from",
            "none",
            "--no-description",
            "--name",
            options.name,
            "--python",
            options.python_version,
            ".",
        ],
        target,
        report["commands"],
        env_overrides=environment,
        sanitize_git=True,
    )
    module = values["MODULE_NAME"]
    expected = {
        ".python-version",
        "pyproject.toml",
        f"src/{module}/__init__.py",
    }
    if options.shape == "library":
        expected.add(f"src/{module}/py.typed")
    created = set(manifest(target)) - set(before_init)
    if created != expected:
        raise BootstrapFailure(
            "official uv init output changed: " + ", ".join(sorted(created)),
            status="partial",
        )
    write_shape_assets(target, options.shape, values)
    install_and_verify(
        options,
        target,
        report,
        create_lock=True,
        install_tools=False,
    )
    history = run_command(
        [options.git, "rev-list", "--all", "--count"],
        target,
        report["commands"],
        sanitize_git=True,
    )
    if history.stdout.strip() != "0":
        raise BootstrapFailure("new repository unexpectedly has commits", status="partial")
    report["verification"]["no_commit"] = "passed"


def bootstrap_existing(options: argparse.Namespace, report: dict[str, Any]) -> None:
    requested = options.target.expanduser().absolute()
    if requested.is_symlink() or not requested.is_dir():
        raise BootstrapFailure("existing target must be a directory", status="blocked")
    target = requested.resolve()
    report["target"] = str(target)
    report["_before"] = manifest(target)
    name, python_version, dependencies, shape = inspect_existing(options, target)
    inspect_mise_lock(
        target,
        python_version,
        options.uv_version,
        options.lefthook_version,
    )
    uv_lock = target / "uv.lock"
    if uv_lock.is_symlink() or not uv_lock.is_file():
        raise BootstrapFailure("existing project requires a regular uv.lock", status="blocked")
    values = values_for(
        name,
        python_version,
        options.uv_version,
        dependencies,
        options.lefthook_version,
        shape,
    )
    report["shape"] = shape
    report["versions"] = {
        "python": python_version,
        "uv": options.uv_version,
        "uv_build": options.uv_version,
        "build": dependencies["build"],
        "mypy": dependencies["mypy"],
        "pytest": dependencies["pytest"],
        "ruff": dependencies["ruff"],
        "lefthook": options.lefthook_version,
    }
    planned = plan_existing_assets(target, common_assets(values))
    mise_lock = target / "mise.lock"
    if mise_lock.is_symlink() or (mise_lock.exists() and not mise_lock.is_file()):
        raise BootstrapFailure("mise.lock is not safely writable", status="blocked")
    for relative, source in planned.items():
        write_asset(target, relative, source)
    (target / ".lefthook" / "partial-stage-guard.sh").chmod(0o755)
    if not mise_lock.exists():
        mise_lock.touch()
    install_and_verify(
        options,
        target,
        report,
        create_lock=False,
    )


def main() -> int:
    options = parse_args()
    target = options.target.expanduser().absolute().resolve(strict=False)
    report_path = options.report.expanduser().absolute().resolve(strict=False)
    if report_path == target or target in report_path.parents:
        print("--report must be outside the target", file=sys.stderr)
        return 2
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": options.mode,
        "stack": "python",
        "shape": options.shape,
        "status": "blocked",
        "target": str(target),
        "versions": {},
        "changes": {"created": [], "modified": [], "deleted": []},
        "commands": [],
        "failed_command": None,
        "error": None,
        "recovery": None,
        "verification": {
            "lefthook": "not-run",
            "mise_run_ci": "not-run",
            "uv_lock": "not-run",
            "no_commit": "not-applicable" if options.mode == "existing" else "not-run",
            "preserved_project_files": (
                "not-run" if options.mode == "existing" else "not-applicable"
            ),
        },
    }
    try:
        validate_versions(options)
        if options.mode == "new":
            bootstrap_new(options, report)
        else:
            bootstrap_existing(options, report)
        before = report["_before"]
        after = manifest(Path(report["target"]))
        report["changes"] = changes(before, after)
        if options.mode == "existing":
            allowed = CORE_BASELINE_PATHS | OPTIONAL_EXISTING_PATHS | {"mise.lock"}
            touched = set(report["changes"]["created"])
            touched.update(report["changes"]["modified"])
            touched.update(report["changes"]["deleted"])
            unexpected = sorted(touched - allowed)
            if unexpected:
                raise BootstrapFailure(
                    "unexpected existing-project mutations: " + ", ".join(unexpected),
                    status="partial",
                )
            report["verification"]["preserved_project_files"] = "passed"
        report.pop("_before")
        report["status"] = "completed"
    except BootstrapFailure as error:
        report["status"] = error.status
        report["failed_command"] = error.failed_command
        report["error"] = str(error)
        report["recovery"] = (
            "Inspect partial changes and rerun the exact failed command after correction."
            if error.status == "partial"
            else "Resolve the reported conflict and rerun inventory."
        )
        if report["verification"]["mise_run_ci"] == "running":
            report["verification"]["mise_run_ci"] = "failed"
        before = report.pop("_before", None)
        target_path = Path(report["target"])
        if isinstance(before, dict) and target_path.is_dir():
            report["changes"] = changes(before, manifest(target_path))
        write_report(options.report, report)
        print(str(error), file=sys.stderr)
        return 1
    write_report(options.report, report)
    print(
        f"completed {options.mode} Python {report['shape']} bootstrap at "
        f"{report['target']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
