#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
EVALS_DIR = ROOT / "evals"
DEFAULT_TIMEOUT = 600
CHANGE_KINDS = ("created", "modified", "deleted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one Skill case in a copied, writable fixture and persist a "
            "before/after report."
        )
    )
    parser.add_argument("--skill", required=True, metavar="NAME")
    parser.add_argument("--case", required=True, dest="case_id", metavar="ID")
    parser.add_argument(
        "--codex",
        default=os.environ.get("CODEX_BIN", "codex"),
        metavar="PATH",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("CODEX_EVAL_MODEL"),
        metavar="MODEL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("CODEX_EVAL_TIMEOUT", DEFAULT_TIMEOUT)),
        metavar="SECONDS",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        metavar="DIRECTORY",
    )
    return parser.parse_args()


def find_skill_path(skill_name: str) -> Path:
    candidates = [
        path.parent
        for path in SKILLS_DIR.rglob("SKILL.md")
        if path.parent.name == skill_name
    ]
    if len(candidates) != 1:
        raise SystemExit(
            f"Expected exactly one Skill named {skill_name!r}, found {len(candidates)}"
        )
    return candidates[0]


def command_available(command: str) -> bool:
    if os.sep in command or (os.altsep and os.altsep in command):
        path = Path(command)
        return path.is_file() and os.access(path, os.X_OK)
    return shutil.which(command) is not None


def load_behavior_case(skill_name: str, case_id: str) -> dict[str, Any]:
    contract_path = EVALS_DIR / f"{skill_name}.behavior.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"Behavior contract not found: {contract_path}") from error
    cases = [entry for entry in contract.get("cases", []) if entry.get("id") == case_id]
    if len(cases) != 1:
        raise SystemExit(
            f"Expected exactly one behavior case {case_id!r}, found {len(cases)}"
        )
    entry = cases[0]
    if entry.get("invocation") != "explicit":
        raise SystemExit("Workspace evaluations require an explicit Skill invocation")
    return entry


def load_workspace_expectation(
    skill_name: str,
    case_id: str,
) -> tuple[Path, dict[str, list[str]]]:
    case_directory = EVALS_DIR / "workspaces" / skill_name / case_id
    input_directory = case_directory / "input"
    expected_path = case_directory / "expected.json"
    if not input_directory.is_dir():
        raise SystemExit(f"Workspace input fixture not found: {input_directory}")
    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"Workspace expectation not found: {expected_path}") from error
    if not isinstance(expected, dict) or expected.get("schema_version") != 1:
        raise SystemExit(f"Workspace expectation must use schema_version 1: {expected_path}")
    changes = expected.get("changes")
    if not isinstance(changes, dict) or set(changes) != set(CHANGE_KINDS):
        raise SystemExit(
            f"Workspace expectation changes must define {', '.join(CHANGE_KINDS)}"
        )
    parsed: dict[str, list[str]] = {}
    for kind in CHANGE_KINDS:
        paths = changes[kind]
        if not isinstance(paths, list) or any(
            not isinstance(path, str) or not safe_relative_path(path) for path in paths
        ):
            raise SystemExit(
                f"Workspace expectation {kind} must contain safe relative paths"
            )
        if len(set(paths)) != len(paths):
            raise SystemExit(f"Workspace expectation {kind} contains duplicates")
        parsed[kind] = sorted(paths)
    return input_directory, parsed


def safe_relative_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def reject_fixture_symlinks(input_directory: Path) -> None:
    for path in input_directory.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"Workspace input fixtures cannot contain symlinks: {path}")


def isolate_skill(skill_name: str, skill_path: Path, workspace: Path) -> str:
    eval_skill_name = f"{skill_name}-working-tree-eval"
    eval_skill_path = workspace / ".agents" / "skills" / eval_skill_name
    eval_skill_path.parent.mkdir(parents=True)
    shutil.copytree(skill_path, eval_skill_path)
    skill_document = eval_skill_path / "SKILL.md"
    source = skill_document.read_text(encoding="utf-8")
    isolated = re.sub(
        rf"\A---\nname: {re.escape(skill_name)}\n",
        f"---\nname: {eval_skill_name}\n",
        source,
        count=1,
    )
    if isolated == source:
        raise SystemExit("Unable to isolate working-tree Skill frontmatter")
    skill_document.write_text(isolated, encoding="utf-8")
    return eval_skill_name


def manifest(workspace: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(workspace.rglob("*")):
        relative_path = path.relative_to(workspace)
        if relative_path.parts and relative_path.parts[0] == ".agents":
            continue
        metadata = path.lstat()
        entry: dict[str, object] = {
            "path": relative_path.as_posix(),
            "mode": stat.S_IMODE(metadata.st_mode),
        }
        if stat.S_ISDIR(metadata.st_mode):
            entry["type"] = "directory"
        elif stat.S_ISLNK(metadata.st_mode):
            entry["type"] = "symlink"
            entry["target"] = os.readlink(path)
        elif stat.S_ISREG(metadata.st_mode):
            data = path.read_bytes()
            entry.update(
                {
                    "type": "file",
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        else:
            entry["type"] = "special"
        entries.append(entry)
    return entries


def workspace_changes(
    before: list[dict[str, object]],
    after: list[dict[str, object]],
) -> dict[str, list[str]]:
    before_by_path = {entry["path"]: entry for entry in before}
    after_by_path = {entry["path"]: entry for entry in after}
    return {
        "created": sorted(after_by_path.keys() - before_by_path.keys()),
        "modified": sorted(
            path
            for path in before_by_path.keys() & after_by_path.keys()
            if before_by_path[path] != after_by_path[path]
        ),
        "deleted": sorted(before_by_path.keys() - after_by_path.keys()),
    }


def compile_patterns(patterns: object, label: str) -> list[re.Pattern[str]]:
    if not isinstance(patterns, list) or any(
        not isinstance(pattern, str) or not pattern for pattern in patterns
    ):
        raise SystemExit(f"{label} must be an array of regular expressions")
    try:
        return [re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in patterns]
    except re.error as error:
        raise SystemExit(f"{label} contains an invalid regular expression: {error}") from error


def answer_failures(entry: dict[str, Any], answer: str) -> list[str]:
    assertions = entry["expected"]["assertions"]
    required = compile_patterns(assertions["required_regex"], "required_regex")
    forbidden = compile_patterns(assertions["forbidden_regex"], "forbidden_regex")
    failures: list[str] = []
    if not answer:
        failures.append("answer is empty")
    failures.extend(
        f"missing required pattern {pattern.pattern!r}"
        for pattern in required
        if not pattern.search(answer)
    )
    failures.extend(
        f"matched forbidden pattern {pattern.pattern!r}"
        for pattern in forbidden
        if pattern.search(answer)
    )
    return failures


def isolated_prompt(entry: dict[str, Any], eval_skill_name: str) -> str:
    return (
        f"Use ${eval_skill_name} for this request.\n"
        "Evaluate only that isolated working-tree Skill. The target workspace is an "
        "isolated fixture; obey the request and the Skill's current write boundary.\n"
        "Return the concise result you would give the user.\n\n"
        f"User request:\n{entry['prompt']}\n"
    )


def run_case(options: argparse.Namespace) -> tuple[dict[str, object], int]:
    if options.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if not command_available(options.codex):
        raise SystemExit(f"Codex executable not found: {options.codex}")
    skill_path = find_skill_path(options.skill)
    entry = load_behavior_case(options.skill, options.case_id)
    input_directory, expected_changes = load_workspace_expectation(
        options.skill,
        options.case_id,
    )
    reject_fixture_symlinks(input_directory)

    with tempfile.TemporaryDirectory(
        prefix=f"{options.skill}-{options.case_id}-workspace-eval-"
    ) as directory:
        eval_root = Path(directory)
        workspace = eval_root / "workspace"
        shutil.copytree(input_directory, workspace)
        eval_skill_name = isolate_skill(options.skill, skill_path, workspace)
        before = manifest(workspace)

        eval_codex_home = eval_root / "codex-home"
        eval_user_home = eval_root / "home"
        eval_codex_home.mkdir()
        eval_user_home.mkdir()
        source_codex_home = Path(
            os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        ).expanduser()
        source_auth = source_codex_home / "auth.json"
        if source_auth.is_file():
            target_auth = eval_codex_home / "auth.json"
            shutil.copyfile(source_auth, target_auth)
            target_auth.chmod(0o600)

        output_path = eval_root / "last-message.txt"
        command = [
            options.codex,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--sandbox",
            "workspace-write",
            "--color",
            "never",
            "--cd",
            str(workspace),
            "--skip-git-repo-check",
            "--output-last-message",
            str(output_path),
        ]
        if options.model:
            command.extend(["--model", options.model])
        command.append("-")
        environment = os.environ.copy()
        environment.update(
            {
                "CODEX_HOME": str(eval_codex_home),
                "HOME": str(eval_user_home),
            }
        )
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                input=isolated_prompt(entry, eval_skill_name),
                env=environment,
                capture_output=True,
                text=True,
                timeout=options.timeout,
                check=False,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as error:
            timed_out = True
            returncode = 124
            stdout = error.stdout or ""
            stderr = error.stderr or ""

        after = manifest(workspace)
        actual_changes = workspace_changes(before, after)
        answer = output_path.read_text(encoding="utf-8").strip() if output_path.is_file() else ""
        failures: list[str] = []
        if timed_out:
            failures.append(f"Codex timed out after {options.timeout} seconds")
        elif returncode != 0:
            failures.append(f"Codex exited with status {returncode}")
        failures.extend(answer_failures(entry, answer))
        if actual_changes != expected_changes:
            failures.append(
                "unexpected workspace changes: "
                f"expected {expected_changes}, got {actual_changes}"
            )

        report: dict[str, object] = {
            "schema_version": 1,
            "skill": options.skill,
            "case": options.case_id,
            "status": "passed" if not failures else "failed",
            "workspace": {
                "before": before,
                "after": after,
                "changes": actual_changes,
            },
            "execution": {
                "command": command,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            },
            "answer": answer,
            "failures": failures,
        }
        return report, 0 if not failures else 1


def main() -> int:
    options = parse_args()
    report, returncode = run_case(options)
    options.report_dir.mkdir(parents=True, exist_ok=True)
    report_path = options.report_dir / f"{options.case_id}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if returncode == 0:
        print(f"[PASS] {options.case_id}: {report_path}")
    else:
        print(f"[FAIL] {options.case_id}: {report_path}", file=sys.stderr)
        for failure in report["failures"]:
            print(f"- {failure}", file=sys.stderr)
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
