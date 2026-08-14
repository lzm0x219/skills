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


ASSETS_DIR = SKILL_DIR / "assets" / "rust"
VERSION_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
NAME_PATTERN = re.compile(r"\A[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*\Z")
IGNORED_ROOTS = {".git", "target"}
BASELINE_PATHS = {
    "mise.toml",
    "lefthook.yml",
    ".lefthook/format-staged-rust.sh",
    ".lefthook/install-hooks.sh",
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
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new or strictly recognized existing Rust package."
    )
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--mode", choices=("new", "existing"), required=True)
    parser.add_argument("--shape", choices=("library", "cli"))
    parser.add_argument("--name")
    parser.add_argument("--rust-version")
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
        ".lefthook/format-staged-rust.sh": render_asset(
            "common/.lefthook/format-staged-rust.sh.tmpl",
            values,
        ),
        ".lefthook/install-hooks.sh": render_asset(
            "common/.lefthook/install-hooks.sh.tmpl",
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


def inspect_rust_toolchain(target: Path, expected: str) -> None:
    toml_path = target / "rust-toolchain.toml"
    plain_path = target / "rust-toolchain"
    if toml_path.exists() and plain_path.exists():
        raise BootstrapFailure(
            "both rust-toolchain.toml and rust-toolchain exist",
            status="blocked",
        )
    if toml_path.is_symlink() or plain_path.is_symlink():
        raise BootstrapFailure("Rust toolchain file cannot be a symlink", status="blocked")
    if toml_path.is_file():
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise BootstrapFailure(
                f"rust-toolchain.toml is invalid: {error}",
                status="blocked",
            ) from error
        channel = data.get("toolchain", {}).get("channel")
        if channel != expected:
            raise BootstrapFailure(
                "Rust version conflict with rust-toolchain.toml",
                status="blocked",
            )
    elif plain_path.is_file():
        if plain_path.read_text(encoding="utf-8").strip() != expected:
            raise BootstrapFailure(
                "Rust version conflict with rust-toolchain",
                status="blocked",
            )


def inspect_existing(
    options: argparse.Namespace,
    target: Path,
) -> tuple[str, str, str]:
    inspect_git_root(target, options.git)
    inspect_alternatives(target)
    cargo_path = target / "Cargo.toml"
    if cargo_path.is_symlink() or not cargo_path.is_file():
        raise BootstrapFailure("Cargo.toml must be a regular file", status="blocked")
    try:
        data = tomllib.loads(cargo_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BootstrapFailure(f"Cargo.toml is invalid: {error}", status="blocked") from error
    package = data.get("package")
    if not isinstance(package, dict):
        raise BootstrapFailure("Cargo.toml must describe one package", status="blocked")
    name = package.get("name")
    rust_version = package.get("rust-version")
    edition = package.get("edition")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise BootstrapFailure("Cargo package name is unsupported", status="blocked")
    if not isinstance(rust_version, str) or not VERSION_PATTERN.fullmatch(rust_version):
        raise BootstrapFailure(
            "Cargo.toml must declare an exact package.rust-version",
            status="blocked",
        )
    if edition != "2024":
        raise BootstrapFailure("only Rust edition 2024 is supported", status="blocked")
    inspect_rust_toolchain(target, rust_version)
    has_library = (target / "src" / "lib.rs").is_file()
    has_cli = (target / "src" / "main.rs").is_file()
    if has_library and not has_cli:
        shape = "library"
    elif has_cli:
        shape = "cli"
    else:
        raise BootstrapFailure("Rust source shape is unsupported", status="blocked")
    if options.shape and options.shape != shape:
        raise BootstrapFailure("requested shape conflicts with Cargo sources", status="blocked")
    return name, rust_version, shape


def values_for(name: str, rust_version: str, lefthook_version: str, shape: str) -> dict[str, str]:
    return {
        "CRATE_NAME": name.replace("-", "_"),
        "LEFTHOOK_VERSION": lefthook_version,
        "PROJECT_NAME": name,
        "PROJECT_SHAPE": "library" if shape == "library" else "CLI application",
        "RUST_VERSION": rust_version,
    }


def validate_versions(rust_version: str | None, lefthook_version: str) -> None:
    if rust_version is not None and not VERSION_PATTERN.fullmatch(rust_version):
        raise BootstrapFailure("--rust-version must be exact x.y.z", status="blocked")
    if not VERSION_PATTERN.fullmatch(lefthook_version):
        raise BootstrapFailure("--lefthook-version must be exact x.y.z", status="blocked")


def plan_existing_assets(
    target: Path,
    assets: dict[str, str],
) -> dict[str, str]:
    planned = {path: assets[path] for path in BASELINE_PATHS}
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


def inspect_mise_lock(target: Path, rust_version: str, lefthook_version: str) -> None:
    path = target / "mise.lock"
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise BootstrapFailure("mise.lock is not safely readable", status="blocked")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BootstrapFailure(f"mise.lock is invalid: {error}", status="blocked") from error
    tools = data.get("tools", {})
    if not isinstance(tools, dict):
        raise BootstrapFailure("mise.lock tools are unsupported", status="blocked")
    for tool, expected in (("rust", rust_version), ("lefthook", lefthook_version)):
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
    generate_cargo_lock: bool,
    install_tools: bool = True,
) -> None:
    commands: list[dict[str, object]] = report["commands"]
    environment = {
        "CARGO_TARGET_DIR": str(target / "target"),
        "MISE_TRUSTED_CONFIG_PATHS": str(target),
    }
    if install_tools:
        run_command(
            [options.mise, "install"],
            target,
            commands,
            env_overrides=environment,
            sanitize_git=True,
        )
    if generate_cargo_lock:
        run_command(
            [options.mise, "exec", "--", "cargo", "generate-lockfile"],
            target,
            commands,
            env_overrides=environment,
            sanitize_git=True,
        )
    run_command(
        [options.mise, "exec", "--", "sh", ".lefthook/install-hooks.sh"],
        target,
        commands,
        env_overrides=environment,
        sanitize_git=True,
    )
    hook = target / ".git" / "hooks" / "pre-commit"
    safe_dispatch = (
        'export MISE_TRUSTED_CONFIG_PATHS="$(git rev-parse --show-toplevel)"; '
        'call_lefthook run "pre-commit" --no-stage-fixed "$@"'
    )
    if (
        not hook.is_file()
        or not os.access(hook, os.X_OK)
        or safe_dispatch not in hook.read_text(encoding="utf-8", errors="replace")
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
        env_overrides=environment,
        sanitize_git=True,
    )
    report["verification"]["mise_run_ci"] = "passed"


def bootstrap_new(options: argparse.Namespace, report: dict[str, Any]) -> None:
    if not options.name or not NAME_PATTERN.fullmatch(options.name):
        raise BootstrapFailure("--name must be a lowercase Cargo package name", status="blocked")
    if not options.shape or not options.rust_version:
        raise BootstrapFailure(
            "new mode requires --shape and --rust-version",
            status="blocked",
        )
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
        options.rust_version,
        options.lefthook_version,
        options.shape,
    )
    report["shape"] = options.shape
    report["versions"] = {
        "rust": options.rust_version,
        "lefthook": options.lefthook_version,
    }
    assets = common_assets(values)
    for relative, source in assets.items():
        write_asset(target, relative, source)
    for relative in (
        ".lefthook/format-staged-rust.sh",
        ".lefthook/install-hooks.sh",
        ".lefthook/partial-stage-guard.sh",
    ):
        (target / relative).chmod(0o755)
    (target / "mise.lock").touch()
    environment = {
        "CARGO_TARGET_DIR": str(target / "target"),
        "MISE_TRUSTED_CONFIG_PATHS": str(target),
    }
    run_command(
        [options.mise, "install"],
        target,
        report["commands"],
        env_overrides=environment,
        sanitize_git=True,
    )
    before_init = manifest(target)
    cargo_shape = "--lib" if options.shape == "library" else "--bin"
    run_command(
        [
            options.mise,
            "exec",
            "--",
            "cargo",
            "init",
            cargo_shape,
            "--edition",
            "2024",
            "--name",
            options.name,
            "--vcs",
            "none",
            ".",
        ],
        target,
        report["commands"],
        env_overrides=environment,
        sanitize_git=True,
    )
    expected = {
        "Cargo.toml",
        "src/lib.rs" if options.shape == "library" else "src/main.rs",
    }
    created = set(manifest(target)) - set(before_init)
    if created != expected:
        raise BootstrapFailure(
            "official cargo init output changed: " + ", ".join(sorted(created)),
            status="partial",
        )
    write_asset(target, "Cargo.toml", render_asset("project/Cargo.toml.tmpl", values))
    shape_root = ASSETS_DIR / options.shape
    for template in shape_root.rglob("*.tmpl"):
        relative = template.relative_to(shape_root)
        write_asset(
            target,
            relative.with_name(relative.name.removesuffix(".tmpl")).as_posix(),
            render_text(template.read_text(encoding="utf-8"), values),
        )
    install_and_verify(
        options,
        target,
        report,
        generate_cargo_lock=True,
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
    name, rust_version, shape = inspect_existing(options, target)
    if options.rust_version and options.rust_version != rust_version:
        raise BootstrapFailure("requested Rust version conflicts with Cargo.toml", status="blocked")
    inspect_mise_lock(target, rust_version, options.lefthook_version)
    cargo_lock = target / "Cargo.lock"
    if cargo_lock.is_symlink() or (cargo_lock.exists() and not cargo_lock.is_file()):
        raise BootstrapFailure("Cargo.lock is not safely readable", status="blocked")
    values = values_for(name, rust_version, options.lefthook_version, shape)
    report["shape"] = shape
    report["versions"] = {
        "rust": rust_version,
        "lefthook": options.lefthook_version,
    }
    planned = plan_existing_assets(target, common_assets(values))
    mise_lock = target / "mise.lock"
    if mise_lock.is_symlink() or (mise_lock.exists() and not mise_lock.is_file()):
        raise BootstrapFailure("mise.lock is not safely writable", status="blocked")
    for relative, source in planned.items():
        write_asset(target, relative, source)
    for relative in (
        ".lefthook/format-staged-rust.sh",
        ".lefthook/install-hooks.sh",
        ".lefthook/partial-stage-guard.sh",
    ):
        (target / relative).chmod(0o755)
    if not mise_lock.exists():
        mise_lock.touch()
    install_and_verify(
        options,
        target,
        report,
        generate_cargo_lock=not (target / "Cargo.lock").is_file(),
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
        "stack": "rust",
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
            "no_commit": "not-applicable" if options.mode == "existing" else "not-run",
            "preserved_project_files": (
                "not-run" if options.mode == "existing" else "not-applicable"
            ),
        },
    }
    try:
        validate_versions(options.rust_version, options.lefthook_version)
        if options.mode == "new":
            bootstrap_new(options, report)
        else:
            bootstrap_existing(options, report)
        before = report["_before"]
        after = manifest(Path(report["target"]))
        report["changes"] = changes(before, after)
        if options.mode == "existing":
            allowed = (
                BASELINE_PATHS
                | OPTIONAL_EXISTING_PATHS
                | {"Cargo.lock", "mise.lock"}
            )
            touched = set(report["changes"]["created"])
            touched.update(report["changes"]["modified"])
            touched.update(report["changes"]["deleted"])
            unexpected = sorted(touched - allowed)
            if unexpected:
                raise BootstrapFailure(
                    "unexpected existing-project mutations: "
                    + ", ".join(unexpected),
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
    print(f"completed {options.mode} Rust {report['shape']} bootstrap at {report['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
