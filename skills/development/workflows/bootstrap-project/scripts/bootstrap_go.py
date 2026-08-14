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


ASSETS_DIR = SKILL_DIR / "assets" / "go"
VERSION_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
GO_DIRECTIVE_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+(?:\.[0-9]+)?\Z")
NAME_PATTERN = re.compile(r"\A[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
PACKAGE_PATTERN = re.compile(r"\A[a-z][a-z0-9_]*\Z")
MODULE_PATH_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._~/-]*\Z")
PACKAGE_DECLARATION = re.compile(r"(?m)^\s*package\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
GO_KEYWORDS = {
    "break",
    "case",
    "chan",
    "const",
    "continue",
    "default",
    "defer",
    "else",
    "fallthrough",
    "for",
    "func",
    "go",
    "goto",
    "if",
    "import",
    "interface",
    "map",
    "package",
    "range",
    "return",
    "select",
    "struct",
    "switch",
    "type",
    "var",
}
IGNORED_NAMES = {".git", "bin", "dist", "vendor"}
CORE_BASELINE_PATHS = {
    "mise.toml",
    "lefthook.yml",
    ".lefthook/check_gofmt.go",
    ".lefthook/format_all_go.go",
    ".lefthook/format_staged_go.go",
    ".lefthook/install_go.go",
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
    "go.work": "Go workspace",
    "go.work.sum": "Go workspace",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new or strictly recognized existing Go module."
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--mode", choices=("new", "existing"), required=True)
    parser.add_argument("--shape", choices=("library", "cli"))
    parser.add_argument("--name")
    parser.add_argument("--module-path")
    parser.add_argument("--go-version")
    parser.add_argument("--lefthook-version", required=True)
    parser.add_argument("--mise", default="mise", metavar="COMMAND")
    parser.add_argument("--git", default="git", metavar="COMMAND")
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def manifest(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        relative_path = path.relative_to(target)
        if any(part in IGNORED_NAMES for part in relative_path.parts):
            continue
        relative = relative_path.as_posix()
        if path.is_symlink():
            result[relative] = "symlink:" + os.readlink(path)
        elif path.is_file():
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def changes(
    before: dict[str, str], after: dict[str, str]
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


def render_asset(relative: str, values: dict[str, str]) -> str:
    source = (ASSETS_DIR / relative).read_text(encoding="utf-8")
    return render_text(source, values)


def write_asset(target: Path, relative: str, source: str) -> None:
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source, encoding="utf-8")


def common_assets(values: dict[str, str]) -> dict[str, str]:
    return {
        "mise.toml": render_asset("common/mise.toml.tmpl", values),
        "lefthook.yml": render_asset("common/lefthook.yml.tmpl", values),
        ".lefthook/check_gofmt.go": render_asset(
            "common/.lefthook/check_gofmt.go.tmpl", values
        ),
        ".lefthook/format_all_go.go": render_asset(
            "common/.lefthook/format_all_go.go.tmpl", values
        ),
        ".lefthook/format_staged_go.go": render_asset(
            "common/.lefthook/format_staged_go.go.tmpl", values
        ),
        ".lefthook/install_go.go": render_asset(
            "common/.lefthook/install_go.go.tmpl", values
        ),
        ".lefthook/partial-stage-guard.sh": render_asset(
            "common/.lefthook/partial-stage-guard.sh.tmpl", values
        ),
        ".github/workflows/validate.yml": render_asset(
            "common/.github/workflows/validate.yml.tmpl", values
        ),
        ".github/renovate.json": render_asset(
            "common/.github/renovate.json.tmpl", values
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


def inspect_alternatives(target: Path) -> None:
    found = [
        f"{relative} indicates {tool}"
        for relative, tool in sorted(ALTERNATIVE_PATHS.items())
        if (target / relative).exists() or (target / relative).is_symlink()
    ]
    if found:
        raise BootstrapFailure(
            "alternative project tools require migration confirmation: "
            + "; ".join(found),
            status="blocked",
        )


def validate_module_path(module_path: str) -> None:
    if (
        not module_path
        or not MODULE_PATH_PATTERN.fullmatch(module_path)
        or module_path.startswith(("/", "."))
        or module_path.endswith(("/", "."))
        or "//" in module_path
        or "@" in module_path
        or "\\" in module_path
        or any(part in ("", ".", "..") for part in module_path.split("/"))
        or any(character.isspace() for character in module_path)
    ):
        raise BootstrapFailure("--module-path is not a safe Go module path", status="blocked")


def parse_go_mod(path: Path) -> tuple[str, str, str | None]:
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure("go.mod must be a regular file", status="blocked")
    module_path: str | None = None
    go_version: str | None = None
    toolchain: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("module "):
            if module_path is not None:
                raise BootstrapFailure("go.mod has duplicate module directives", status="blocked")
            module_path = line.removeprefix("module ").strip()
        elif line.startswith("go "):
            if go_version is not None:
                raise BootstrapFailure("go.mod has duplicate go directives", status="blocked")
            go_version = line.removeprefix("go ").strip()
        elif line.startswith("toolchain "):
            if toolchain is not None:
                raise BootstrapFailure(
                    "go.mod has duplicate toolchain directives", status="blocked"
                )
            toolchain = line.removeprefix("toolchain ").strip()
    if module_path is None or go_version is None:
        raise BootstrapFailure("go.mod requires module and go directives", status="blocked")
    validate_module_path(module_path)
    if not GO_DIRECTIVE_PATTERN.fullmatch(go_version):
        raise BootstrapFailure("go.mod go directive is unsupported", status="blocked")
    if toolchain is not None and not re.fullmatch(r"go[0-9]+\.[0-9]+\.[0-9]+", toolchain):
        raise BootstrapFailure("go.mod toolchain directive is unsupported", status="blocked")
    return module_path, go_version, toolchain


def read_mise_versions(target: Path) -> tuple[str | None, str | None]:
    path = target / "mise.toml"
    if not path.exists():
        return None, None
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure("mise.toml is not safely readable", status="blocked")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BootstrapFailure(f"mise.toml is invalid: {error}", status="blocked") from error
    tools = data.get("tools", {})
    if not isinstance(tools, dict):
        raise BootstrapFailure("mise.toml tools are unsupported", status="blocked")
    go_version = tools.get("go")
    lefthook_version = tools.get("lefthook")
    for name, version in (("go", go_version), ("lefthook", lefthook_version)):
        if version is not None and (
            not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version)
        ):
            raise BootstrapFailure(
                f"mise.toml {name} version must be exact",
                status="blocked",
            )
    return go_version, lefthook_version


def resolve_existing_go_version(
    requested: str | None,
    mise_version: str | None,
    directive: str,
    toolchain: str | None,
) -> str:
    candidates = [value for value in (requested, mise_version) if value is not None]
    if toolchain is not None:
        candidates.append(toolchain.removeprefix("go"))
    if len(directive.split(".")) == 3:
        candidates.append(directive)
    if not candidates:
        raise BootstrapFailure(
            "existing mode requires --go-version or an exact repository constraint",
            status="blocked",
        )
    resolved = candidates[0]
    if any(candidate != resolved for candidate in candidates[1:]):
        raise BootstrapFailure("Go version constraints disagree", status="blocked")
    if directive != resolved and ".".join(resolved.split(".")[:2]) != directive:
        raise BootstrapFailure(
            "exact Go version does not satisfy the go.mod go directive",
            status="blocked",
        )
    return resolved


def project_go_files(target: Path) -> list[Path]:
    files: list[Path] = []
    for path in target.rglob("*.go"):
        relative = path.relative_to(target)
        if any(part.startswith(".") or part == "vendor" for part in relative.parts[:-1]):
            continue
        if path.is_symlink() or not path.is_file():
            raise BootstrapFailure(
                f"Go source is not a regular file: {relative.as_posix()}",
                status="blocked",
            )
        files.append(path)
    return sorted(files)


def inspect_shape(target: Path) -> tuple[str, str]:
    files = project_go_files(target)
    source_files = [path for path in files if not path.name.endswith("_test.go")]
    test_files = [path for path in files if path.name.endswith("_test.go")]
    if not source_files or not test_files:
        raise BootstrapFailure(
            "existing Go project requires source files and tests",
            status="blocked",
        )
    packages: dict[Path, str] = {}
    for path in files:
        match = PACKAGE_DECLARATION.search(path.read_text(encoding="utf-8"))
        if match is None:
            raise BootstrapFailure(
                f"cannot recognize package declaration in {path.relative_to(target)}",
                status="blocked",
            )
        packages[path] = match.group(1)
    main_directories = {
        path.parent
        for path in source_files
        if packages[path] == "main"
    }
    if len(main_directories) > 1:
        raise BootstrapFailure("multiple Go commands are outside the v1 boundary", status="blocked")
    shape = "cli" if main_directories else "library"
    non_main_source_packages = [
        packages[path] for path in source_files if packages[path] != "main"
    ]
    if shape == "cli":
        command_directory = next(iter(main_directories)).relative_to(target)
        if (
            len(command_directory.parts) != 2
            or command_directory.parts[0] != "cmd"
            or not non_main_source_packages
        ):
            raise BootstrapFailure(
                "existing CLI requires one cmd/<name> entry and a testable library package",
                status="blocked",
            )
    package_name = non_main_source_packages[0] if non_main_source_packages else packages[source_files[0]]
    non_main_packages = [
        package for package in packages.values() if package not in ("main", "main_test")
    ]
    normalized_packages = [
        package.removesuffix("_test") for package in non_main_packages
    ]
    if any(package != package_name for package in normalized_packages):
        raise BootstrapFailure("multiple Go package names are outside the v1 boundary", status="blocked")
    return shape, package_name


def values_for(
    name: str,
    module_path: str,
    package_name: str,
    go_version: str,
    lefthook_version: str,
    shape: str,
) -> dict[str, str]:
    return {
        "PROJECT_NAME": name,
        "MODULE_PATH": module_path,
        "PACKAGE_NAME": package_name,
        "COMMAND_NAME": name,
        "GO_VERSION": go_version,
        "LEFTHOOK_VERSION": lefthook_version,
        "SHAPE_LABEL": "library" if shape == "library" else "CLI application",
    }


def validate_versions(options: argparse.Namespace) -> None:
    for label, version in (
        ("Go", options.go_version),
        ("Lefthook", options.lefthook_version),
    ):
        if version is not None and not VERSION_PATTERN.fullmatch(version):
            raise BootstrapFailure(f"{label} version must be exact x.y.z", status="blocked")


def plan_existing_assets(target: Path, assets: dict[str, str]) -> dict[str, str]:
    planned: dict[str, str] = {}
    for relative, source in assets.items():
        path = target / relative
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise BootstrapFailure(f"{relative} is not safely writable", status="blocked")
        if not path.exists():
            planned[relative] = source
            continue
        existing = path.read_text(encoding="utf-8")
        if relative in CORE_BASELINE_PATHS and existing != source:
            raise BootstrapFailure(
                f"existing {relative} differs from the recognized Go baseline",
                status="blocked",
            )
    return planned


def inspect_mise_lock(
    target: Path,
    go_version: str,
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
    for tool, expected in (("go", go_version), ("lefthook", lefthook_version)):
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
    new_module: bool,
    install_tools: bool = True,
) -> None:
    commands: list[dict[str, object]] = report["commands"]
    environment = {
        "MISE_TRUSTED_CONFIG_PATHS": str(target),
        "GOTOOLCHAIN": "local",
        "GOWORK": "off",
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
        report["versions"]["go"],
        report["versions"]["lefthook"],
    )
    tidy_command = [options.mise, "exec", "--", "go", "mod", "tidy"]
    if not new_module:
        tidy_command.append("-diff")
    run_command(
        tidy_command,
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    report["verification"]["go_mod"] = "passed"
    hook_command = [
        options.mise,
        "exec",
        "--",
        "go",
        "run",
        ".lefthook/install_go.go",
    ]
    run_command(
        hook_command,
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
            failed_command=hook_command,
        )
    hook_source = hook.read_text(encoding="utf-8", errors="replace")
    if 'run "pre-commit" --no-stage-fixed' not in hook_source:
        raise BootstrapFailure(
            "installed pre-commit hook is missing the partial-stage safety flag",
            status="partial",
            failed_command=hook_command,
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
    command_name = values["COMMAND_NAME"]
    for template in shape_root.rglob("*.tmpl"):
        relative = template.relative_to(shape_root)
        parts = [command_name if part == "command" else part for part in relative.parts]
        destination = Path(*parts)
        destination = destination.with_name(destination.name.removesuffix(".tmpl"))
        write_asset(
            target,
            destination.as_posix(),
            render_text(template.read_text(encoding="utf-8"), values),
        )


def bootstrap_new(options: argparse.Namespace, report: dict[str, Any]) -> None:
    if not options.name or not NAME_PATTERN.fullmatch(options.name):
        raise BootstrapFailure("--name must be a lowercase Go project name", status="blocked")
    if not options.module_path:
        raise BootstrapFailure("new mode requires --module-path", status="blocked")
    validate_module_path(options.module_path)
    if not options.shape or not options.go_version:
        raise BootstrapFailure(
            "new mode requires --shape and --go-version",
            status="blocked",
        )
    package_name = options.name.replace("-", "_")
    if not PACKAGE_PATTERN.fullmatch(package_name) or package_name in GO_KEYWORDS:
        raise BootstrapFailure("project name cannot form a Go package name", status="blocked")
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
        options.module_path,
        package_name,
        options.go_version,
        options.lefthook_version,
        options.shape,
    )
    report["shape"] = options.shape
    report["versions"] = {
        "go": options.go_version,
        "lefthook": options.lefthook_version,
    }
    report["module_path"] = options.module_path
    for relative, source in common_assets(values).items():
        write_asset(target, relative, source)
    (target / ".lefthook" / "partial-stage-guard.sh").chmod(0o755)
    (target / "mise.lock").touch()
    environment = {
        "MISE_TRUSTED_CONFIG_PATHS": str(target),
        "GOTOOLCHAIN": "local",
        "GOWORK": "off",
    }
    run_command(
        [options.mise, "install"],
        target,
        report["commands"],
        env_overrides=environment,
        sanitize_git=True,
    )
    before_init = manifest(target)
    init_command = [
        options.mise,
        "exec",
        "--",
        "go",
        "mod",
        "init",
        options.module_path,
    ]
    run_command(
        init_command,
        target,
        report["commands"],
        env_overrides=environment,
        sanitize_git=True,
    )
    created = set(manifest(target)) - set(before_init)
    if created != {"go.mod"}:
        raise BootstrapFailure(
            "official go mod init output changed: " + ", ".join(sorted(created)),
            status="partial",
        )
    module_path, directive, toolchain = parse_go_mod(target / "go.mod")
    if module_path != options.module_path or directive != options.go_version:
        raise BootstrapFailure(
            "go mod init produced unexpected module or Go version metadata",
            status="partial",
            failed_command=init_command,
        )
    if toolchain not in (None, "go" + options.go_version):
        raise BootstrapFailure(
            "go mod init produced an unexpected toolchain directive",
            status="partial",
            failed_command=init_command,
        )
    write_shape_assets(target, options.shape, values)
    install_and_verify(
        options,
        target,
        report,
        new_module=True,
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


def inspect_existing(
    options: argparse.Namespace,
    target: Path,
) -> tuple[str, str, str, str, str]:
    inspect_git_root(target, options.git)
    inspect_alternatives(target)
    nested_modules = [
        path
        for path in target.rglob("go.mod")
        if path != target / "go.mod" and ".git" not in path.relative_to(target).parts
    ]
    if nested_modules:
        raise BootstrapFailure("nested Go modules are outside the v1 boundary", status="blocked")
    module_path, directive, toolchain = parse_go_mod(target / "go.mod")
    if options.module_path is not None and options.module_path != module_path:
        raise BootstrapFailure("--module-path conflicts with go.mod", status="blocked")
    mise_go, mise_lefthook = read_mise_versions(target)
    if mise_lefthook is not None and mise_lefthook != options.lefthook_version:
        raise BootstrapFailure("Lefthook version constraints disagree", status="blocked")
    go_version = resolve_existing_go_version(
        options.go_version,
        mise_go,
        directive,
        toolchain,
    )
    shape, package_name = inspect_shape(target)
    if options.shape is not None and options.shape != shape:
        raise BootstrapFailure("--shape conflicts with Go sources", status="blocked")
    inferred_name = module_path.rstrip("/").rsplit("/", 1)[-1].lower()
    if options.name is not None and options.name != inferred_name:
        raise BootstrapFailure("--name conflicts with the module path", status="blocked")
    name = options.name or inferred_name
    if not NAME_PATTERN.fullmatch(name):
        raise BootstrapFailure(
            "module path does not provide a supported project name",
            status="blocked",
        )
    return name, module_path, package_name, go_version, shape


def bootstrap_existing(options: argparse.Namespace, report: dict[str, Any]) -> None:
    requested = options.target.expanduser().absolute()
    if requested.is_symlink() or not requested.is_dir():
        raise BootstrapFailure("existing target must be a directory", status="blocked")
    target = requested.resolve()
    report["target"] = str(target)
    report["_before"] = manifest(target)
    name, module_path, package_name, go_version, shape = inspect_existing(
        options, target
    )
    inspect_mise_lock(target, go_version, options.lefthook_version)
    values = values_for(
        name,
        module_path,
        package_name,
        go_version,
        options.lefthook_version,
        shape,
    )
    report["shape"] = shape
    report["versions"] = {
        "go": go_version,
        "lefthook": options.lefthook_version,
    }
    report["module_path"] = module_path
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
        new_module=False,
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
        "stack": "go",
        "shape": options.shape,
        "status": "blocked",
        "target": str(target),
        "module_path": None,
        "versions": {},
        "changes": {"created": [], "modified": [], "deleted": []},
        "commands": [],
        "failed_command": None,
        "error": None,
        "recovery": None,
        "verification": {
            "lefthook": "not-run",
            "mise_run_ci": "not-run",
            "go_mod": "not-run",
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
    print(f"completed {options.mode} Go {report['shape']} bootstrap at {report['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
