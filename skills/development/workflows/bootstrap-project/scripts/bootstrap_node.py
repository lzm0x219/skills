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
    BootstrapFailure,
    SKILL_DIR,
    render_text,
    run_command,
    write_report,
)


ASSETS_DIR = SKILL_DIR / "assets" / "node"
VERSION_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
NAME_PATTERN = re.compile(
    r"\A(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*\Z"
)
IGNORED_ROOTS = {".git", ".vitest", "coverage", "dist", "node_modules"}
CORE_BASELINE_PATHS = {
    "mise.toml",
    "lefthook.yml",
    ".lefthook/format-staged-node.mjs",
    ".lefthook/install-node.mjs",
    ".lefthook/partial-stage-guard.sh",
    ".github/workflows/validate.yml",
    ".github/renovate.json",
}
COMPATIBLE_CONFIG_PATHS = {
    "pnpm-workspace.yaml",
    ".oxlintrc.json",
    "vitest.config.ts",
    "tsconfig.json",
    "tsconfig.build.json",
}
OPTIONAL_EXISTING_PATHS = {".editorconfig", ".gitignore", "README.md"}
ALTERNATIVE_PATHS = {
    ".husky": "Husky",
    ".pre-commit-config.yaml": "pre-commit",
    ".pre-commit-config.yml": "pre-commit",
    ".tool-versions": "asdf",
    "bun.lock": "Bun",
    "bun.lockb": "Bun",
    "eslint.config.js": "ESLint",
    "eslint.config.mjs": "ESLint",
    "eslint.config.ts": "ESLint",
    "package-lock.json": "npm",
    "yarn.lock": "Yarn",
}
FORBIDDEN_DEPENDENCIES = {
    "@typescript-eslint/eslint-plugin",
    "@typescript-eslint/parser",
    "eslint",
    "husky",
    "lint-staged",
    "prettier",
    "typescript-eslint",
}
DEPENDENCY_ARGUMENTS = {
    "@types/node": "node_types_version",
    "oxfmt": "oxfmt_version",
    "oxlint": "oxlint_version",
    "typescript": "typescript_version",
    "vitest": "vitest_version",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap a new or strictly recognized existing TypeScript/Node.js "
            "package."
        )
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--mode", choices=("new", "existing"), required=True)
    parser.add_argument("--shape", choices=("library", "cli"))
    parser.add_argument("--name")
    parser.add_argument("--node-version")
    parser.add_argument("--pnpm-version")
    parser.add_argument("--typescript-version")
    parser.add_argument("--node-types-version")
    parser.add_argument("--oxfmt-version")
    parser.add_argument("--oxlint-version")
    parser.add_argument("--vitest-version")
    parser.add_argument("--lefthook-version", required=True)
    parser.add_argument("--mise", default="mise", metavar="COMMAND")
    parser.add_argument("--git", default="git", metavar="COMMAND")
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def manifest(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        relative = path.relative_to(target)
        if relative.parts and relative.parts[0] in IGNORED_ROOTS:
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
        ".lefthook/partial-stage-guard.sh": render_asset(
            "common/.lefthook/partial-stage-guard.sh.tmpl",
            values,
        ),
        ".lefthook/format-staged-node.mjs": render_asset(
            "common/.lefthook/format-staged-node.mjs.tmpl",
            values,
        ),
        ".lefthook/install-node.mjs": render_asset(
            "common/.lefthook/install-node.mjs.tmpl",
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
        "pnpm-workspace.yaml": render_asset(
            "common/pnpm-workspace.yaml.tmpl",
            values,
        ),
        ".oxlintrc.json": render_asset("common/.oxlintrc.json.tmpl", values),
        "vitest.config.ts": render_asset("common/vitest.config.ts.tmpl", values),
        "tsconfig.json": render_asset("common/tsconfig.json.tmpl", values),
        "tsconfig.build.json": render_asset(
            "common/tsconfig.build.json.tmpl",
            values,
        ),
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


def dependency_sections(package: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for name in ("dependencies", "devDependencies", "optionalDependencies"):
        value = package.get(name)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise BootstrapFailure(f"package.json {name} must be an object", status="blocked")
        sections.append(value)
    return sections


def inspect_alternatives(target: Path, package: dict[str, Any]) -> None:
    found = [
        f"{relative} indicates {tool}"
        for relative, tool in sorted(ALTERNATIVE_PATHS.items())
        if (target / relative).exists() or (target / relative).is_symlink()
    ]
    for path in target.iterdir():
        if path.name.startswith((".eslintrc", ".prettierrc")):
            found.append(f"{path.name} indicates an alternative quality tool")
    if package.get("volta") is not None:
        found.append("package.json volta indicates Volta")
    installed = {
        name
        for section in dependency_sections(package)
        for name in section
        if isinstance(name, str)
    }
    for dependency in sorted(installed & FORBIDDEN_DEPENDENCIES):
        found.append(f"package dependency {dependency} requires migration confirmation")
    if found:
        raise BootstrapFailure(
            "alternative project tools require migration confirmation: "
            + "; ".join(found),
            status="blocked",
        )


def load_package(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure("package.json must be a regular file", status="blocked")
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BootstrapFailure(
            f"package.json is invalid: {error}",
            status="blocked",
        ) from error
    if not isinstance(package, dict):
        raise BootstrapFailure("package.json must be an object", status="blocked")
    return package


def exact_version(existing: Any, requested: str | None, label: str) -> str:
    if existing is not None:
        if not isinstance(existing, str) or not VERSION_PATTERN.fullmatch(existing):
            raise BootstrapFailure(f"{label} must be an exact x.y.z version", status="blocked")
        if requested and requested != existing:
            raise BootstrapFailure(
                f"requested {label} conflicts with package metadata",
                status="blocked",
            )
        return existing
    if requested is None:
        raise BootstrapFailure(
            f"{label} is missing; provide an exact version",
            status="blocked",
        )
    return requested


def installed_dependency_version(package: dict[str, Any], name: str) -> Any:
    found: list[Any] = []
    for section in dependency_sections(package):
        if name in section:
            found.append(section[name])
    if len(found) > 1 and any(value != found[0] for value in found[1:]):
        raise BootstrapFailure(
            f"package.json declares conflicting {name} versions",
            status="blocked",
        )
    return found[0] if found else None


def inspect_shape(target: Path, package: dict[str, Any]) -> str:
    nested_packages = [
        path
        for path in target.rglob("package.json")
        if path != target / "package.json" and "node_modules" not in path.parts
    ]
    if nested_packages:
        raise BootstrapFailure(
            "multiple package.json files require an exact subproject target",
            status="blocked",
        )
    has_index = (target / "src" / "index.ts").is_file()
    has_cli = (target / "src" / "cli.ts").is_file()
    if package.get("bin") is not None or has_cli:
        shape = "cli"
    elif package.get("exports") is not None or has_index:
        shape = "library"
    else:
        raise BootstrapFailure("TypeScript source shape is unsupported", status="blocked")
    if not has_index or (shape == "cli" and not has_cli):
        raise BootstrapFailure("recognized TypeScript source files are missing", status="blocked")
    tests = [path for path in (target / "test").rglob("*.test.ts") if path.is_file()]
    if not tests:
        raise BootstrapFailure("existing project requires a Vitest smoke test", status="blocked")
    return shape


def inspect_tsconfig(target: Path) -> None:
    path = target / "tsconfig.json"
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure("tsconfig.json is not safely readable", status="blocked")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BootstrapFailure(f"tsconfig.json is invalid: {error}", status="blocked") from error
    compiler = data.get("compilerOptions") if isinstance(data, dict) else None
    required = {
        "module": "NodeNext",
        "moduleResolution": "NodeNext",
        "noEmit": True,
        "strict": True,
    }
    if not isinstance(compiler, dict) or any(
        compiler.get(name) != expected for name, expected in required.items()
    ):
        raise BootstrapFailure(
            "existing tsconfig.json is not a compatible strict NodeNext baseline",
            status="blocked",
        )


def inspect_existing(
    options: argparse.Namespace,
    target: Path,
) -> tuple[dict[str, Any], str, str, str, dict[str, str], str]:
    inspect_git_root(target, options.git)
    package = load_package(target / "package.json")
    inspect_alternatives(target, package)
    inspect_tsconfig(target)
    name = package.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise BootstrapFailure("npm package name is unsupported", status="blocked")
    if package.get("type") != "module":
        raise BootstrapFailure('existing package.json must declare "type": "module"', status="blocked")
    engines = package.get("engines")
    if engines is None:
        engines = {}
    if not isinstance(engines, dict):
        raise BootstrapFailure("package.json engines must be an object", status="blocked")
    node_version = exact_version(engines.get("node"), options.node_version, "Node")
    package_manager = package.get("packageManager")
    existing_pnpm: str | None = None
    if package_manager is not None:
        if not isinstance(package_manager, str) or not package_manager.startswith("pnpm@"):
            raise BootstrapFailure("packageManager must use exact pnpm", status="blocked")
        existing_pnpm = package_manager.removeprefix("pnpm@")
    pnpm_version = exact_version(existing_pnpm, options.pnpm_version, "pnpm")
    if "pnpm" in engines:
        exact_version(engines["pnpm"], pnpm_version, "pnpm engine")
    versions: dict[str, str] = {}
    for dependency, argument in DEPENDENCY_ARGUMENTS.items():
        versions[dependency] = exact_version(
            installed_dependency_version(package, dependency),
            getattr(options, argument),
            dependency,
        )
    shape = inspect_shape(target, package)
    if options.shape and options.shape != shape:
        raise BootstrapFailure("requested shape conflicts with package sources", status="blocked")
    return package, name, node_version, pnpm_version, versions, shape


def merge_package(
    package: dict[str, Any],
    node_version: str,
    pnpm_version: str,
    dependency_versions: dict[str, str],
) -> str:
    merged = json.loads(json.dumps(package))
    engines = merged.setdefault("engines", {})
    engines.setdefault("node", node_version)
    engines.setdefault("pnpm", pnpm_version)
    merged.setdefault("packageManager", f"pnpm@{pnpm_version}")
    dev_dependencies = merged.setdefault("devDependencies", {})
    if not isinstance(dev_dependencies, dict):
        raise BootstrapFailure("package.json devDependencies must be an object", status="blocked")
    installed = {
        name
        for section in dependency_sections(merged)
        for name in section
        if isinstance(name, str)
    }
    for name, version in dependency_versions.items():
        if name not in installed:
            dev_dependencies[name] = version
    return json.dumps(merged, ensure_ascii=False, indent=2) + "\n"


def values_for(
    name: str,
    node_version: str,
    pnpm_version: str,
    dependency_versions: dict[str, str],
    lefthook_version: str,
    shape: str,
) -> dict[str, str]:
    return {
        "BIN_NAME": name.rsplit("/", 1)[-1],
        "LEFTHOOK_VERSION": lefthook_version,
        "NODE_TYPES_VERSION": dependency_versions["@types/node"],
        "NODE_VERSION": node_version,
        "OXFMT_VERSION": dependency_versions["oxfmt"],
        "OXLINT_VERSION": dependency_versions["oxlint"],
        "PNPM_VERSION": pnpm_version,
        "PROJECT_NAME": name,
        "PROJECT_SHAPE": "library" if shape == "library" else "CLI application",
        "TYPESCRIPT_VERSION": dependency_versions["typescript"],
        "VITEST_VERSION": dependency_versions["vitest"],
    }


def validate_versions(options: argparse.Namespace) -> None:
    fields = (
        "node_version",
        "pnpm_version",
        "typescript_version",
        "node_types_version",
        "oxfmt_version",
        "oxlint_version",
        "vitest_version",
        "lefthook_version",
    )
    for field in fields:
        value = getattr(options, field)
        if value is not None and not VERSION_PATTERN.fullmatch(value):
            flag = "--" + field.replace("_", "-")
            raise BootstrapFailure(f"{flag} must be exact x.y.z", status="blocked")


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
    for relative in COMPATIBLE_CONFIG_PATHS | OPTIONAL_EXISTING_PATHS:
        path = target / relative
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise BootstrapFailure(f"{relative} is not safely writable", status="blocked")
        if not path.exists():
            planned[relative] = assets[relative]
    return planned


def inspect_mise_lock(
    target: Path,
    node_version: str,
    pnpm_version: str,
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
        ("node", node_version),
        ("pnpm", pnpm_version),
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
    install_tools: bool = True,
) -> None:
    commands: list[dict[str, object]] = report["commands"]
    environment = {"MISE_TRUSTED_CONFIG_PATHS": str(target)}
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
        report["versions"]["node"],
        report["versions"]["pnpm"],
        report["versions"]["lefthook"],
    )
    run_command(
        [options.mise, "exec", "--", "pnpm", "install", "--lockfile-only"],
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    run_command(
        [options.mise, "exec", "--", "pnpm", "install", "--frozen-lockfile"],
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    if not (target / "pnpm-lock.yaml").is_file():
        raise BootstrapFailure(
            "pnpm did not create pnpm-lock.yaml",
            status="partial",
            failed_command=[
                options.mise,
                "exec",
                "--",
                "pnpm",
                "install",
                "--lockfile-only",
            ],
        )
    report["verification"]["pnpm_lock"] = "passed"
    run_command(
        [options.mise, "exec", "--", "node", ".lefthook/install-node.mjs"],
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
                "node",
                ".lefthook/install-node.mjs",
            ],
        )
    hook_source = hook.read_text(encoding="utf-8", errors="replace")
    safe_dispatch = (
        'export MISE_TRUSTED_CONFIG_PATHS="$(git rev-parse --show-toplevel)"; '
        'call_lefthook run "pre-commit" --no-stage-fixed "$@"'
    )
    if safe_dispatch not in hook_source:
        raise BootstrapFailure(
            "installed pre-commit hook is missing its scoped trust or safety flag",
            status="partial",
            failed_command=[
                options.mise,
                "exec",
                "--",
                "node",
                ".lefthook/install-node.mjs",
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


def bootstrap_new(options: argparse.Namespace, report: dict[str, Any]) -> None:
    if not options.name or not NAME_PATTERN.fullmatch(options.name):
        raise BootstrapFailure("--name must be a lowercase npm package name", status="blocked")
    if not options.shape or not options.node_version or not options.pnpm_version:
        raise BootstrapFailure(
            "new mode requires --shape, --node-version, and --pnpm-version",
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
        options.node_version,
        options.pnpm_version,
        dependency_versions,
        options.lefthook_version,
        options.shape,
    )
    report["shape"] = options.shape
    report["versions"] = {
        "node": options.node_version,
        "pnpm": options.pnpm_version,
        "typescript": dependency_versions["typescript"],
        "node_types": dependency_versions["@types/node"],
        "oxfmt": dependency_versions["oxfmt"],
        "oxlint": dependency_versions["oxlint"],
        "vitest": dependency_versions["vitest"],
        "lefthook": options.lefthook_version,
    }
    for relative, source in common_assets(values).items():
        write_asset(target, relative, source)
    shape_root = ASSETS_DIR / options.shape
    for template in shape_root.rglob("*.tmpl"):
        relative = template.relative_to(shape_root)
        write_asset(
            target,
            relative.with_name(relative.name.removesuffix(".tmpl")).as_posix(),
            render_text(template.read_text(encoding="utf-8"), values),
        )
    (target / ".lefthook" / "partial-stage-guard.sh").chmod(0o755)
    (target / "mise.lock").touch()
    install_and_verify(options, target, report)
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
    package, name, node_version, pnpm_version, dependencies, shape = inspect_existing(
        options,
        target,
    )
    inspect_mise_lock(target, node_version, pnpm_version, options.lefthook_version)
    pnpm_lock = target / "pnpm-lock.yaml"
    if pnpm_lock.is_symlink() or (pnpm_lock.exists() and not pnpm_lock.is_file()):
        raise BootstrapFailure("pnpm-lock.yaml is not safely readable", status="blocked")
    values = values_for(
        name,
        node_version,
        pnpm_version,
        dependencies,
        options.lefthook_version,
        shape,
    )
    report["shape"] = shape
    report["versions"] = {
        "node": node_version,
        "pnpm": pnpm_version,
        "typescript": dependencies["typescript"],
        "node_types": dependencies["@types/node"],
        "oxfmt": dependencies["oxfmt"],
        "oxlint": dependencies["oxlint"],
        "vitest": dependencies["vitest"],
        "lefthook": options.lefthook_version,
    }
    planned = plan_existing_assets(target, common_assets(values))
    package_source = merge_package(
        package,
        node_version,
        pnpm_version,
        dependencies,
    )
    if (target / "package.json").read_text(encoding="utf-8") != package_source:
        planned["package.json"] = package_source
    mise_lock = target / "mise.lock"
    if mise_lock.is_symlink() or (mise_lock.exists() and not mise_lock.is_file()):
        raise BootstrapFailure("mise.lock is not safely writable", status="blocked")
    for relative, source in planned.items():
        write_asset(target, relative, source)
    (target / ".lefthook" / "partial-stage-guard.sh").chmod(0o755)
    if not mise_lock.exists():
        mise_lock.touch()
    install_and_verify(options, target, report)


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
        "stack": "typescript-node",
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
            "pnpm_lock": "not-run",
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
            allowed = (
                CORE_BASELINE_PATHS
                | COMPATIBLE_CONFIG_PATHS
                | OPTIONAL_EXISTING_PATHS
                | {"mise.lock", "package.json", "pnpm-lock.yaml"}
            )
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
        f"completed {options.mode} TypeScript/Node.js {report['shape']} "
        f"bootstrap at {report['target']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
