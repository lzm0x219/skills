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


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
EVALS_DIR = ROOT / "evals"
DEFAULT_SKILL = "dsa-design"


def environment_timeout() -> int:
    raw_timeout = os.environ.get("CODEX_EVAL_TIMEOUT", "600")
    try:
        return int(raw_timeout)
    except ValueError as error:
        raise SystemExit(
            f"CODEX_EVAL_TIMEOUT must be an integer, got {raw_timeout!r}"
        ) from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Skill's behavior contract against Codex or saved answers."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list available behavior cases without calling a model",
    )
    parser.add_argument(
        "--skill",
        default=DEFAULT_SKILL,
        metavar="NAME",
        help=f"evaluate a discovered Skill (default: {DEFAULT_SKILL})",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        dest="case_ids",
        metavar="ID",
        help="run one case; repeat to run several",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        metavar="DIRECTORY",
        help="validate saved answers instead of calling Codex",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("CODEX_EVAL_MODEL"),
        metavar="MODEL",
        help="override the Codex model",
    )
    parser.add_argument(
        "--codex",
        default=os.environ.get("CODEX_BIN", "codex"),
        metavar="PATH",
        help="Codex executable or command name",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=environment_timeout(),
        metavar="SECONDS",
        help="per-case timeout",
    )
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="print successful model outputs",
    )
    return parser.parse_args()


def find_skill_path(skill_name: str) -> Path:
    candidates = [
        skill_document.parent
        for skill_document in SKILLS_DIR.glob("**/SKILL.md")
        if skill_document.parent.name == skill_name
    ]
    if not candidates:
        raise SystemExit(f"No Skill named {skill_name!r} found below {SKILLS_DIR}")
    if len(candidates) > 1:
        raise SystemExit(
            f"More than one Skill named {skill_name!r} found below {SKILLS_DIR}"
        )
    return candidates[0]


def command_available(command: str) -> bool:
    if os.sep in command or (os.altsep and os.altsep in command):
        path = Path(command)
        return path.is_file() and os.access(path, os.X_OK)
    return shutil.which(command) is not None


def compile_patterns(patterns: list[str], label: str) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE | re.MULTILINE))
        except re.error as error:
            raise SystemExit(
                f"{label}: invalid regular expression {pattern!r}: {error}"
            ) from error
    return compiled


def isolated_prompt(
    entry: dict[str, object],
    eval_skill_name: str,
    case_id: str,
) -> str:
    invocation = entry["invocation"]
    user_prompt = entry["prompt"]
    if invocation == "explicit":
        return (
            f"Use ${eval_skill_name} to answer this user request.\n"
            "Evaluate only that isolated working-tree skill; do not use an installed "
            "skill with a similar name.\n"
            "This is a read-only behavior evaluation: do not modify files.\n"
            "Return only the concise answer you would give the user.\n\n"
            f"User request:\n{user_prompt}\n"
        )
    if invocation == "implicit":
        return (
            "Answer this user request in the current workspace. This is a read-only "
            "behavior evaluation: do not modify files.\n"
            "Return only the concise answer you would give the user.\n\n"
            f"User request:\n{user_prompt}\n"
        )
    raise SystemExit(f"{case_id}.invocation must be explicit or implicit")


def prepare_isolated_workspace(
    skill_name: str,
    skill_path: Path,
    eval_root: Path,
) -> tuple[Path, Path, Path, str]:
    eval_workspace = eval_root / "workspace"
    eval_codex_home = eval_root / "codex-home"
    eval_user_home = eval_root / "home"
    eval_workspace.mkdir()
    eval_codex_home.mkdir()
    eval_user_home.mkdir()

    source_codex_home = Path(
        os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
    ).expanduser()
    source_auth_path = source_codex_home / "auth.json"
    if source_auth_path.is_file():
        isolated_auth_path = eval_codex_home / "auth.json"
        shutil.copyfile(source_auth_path, isolated_auth_path)
        isolated_auth_path.chmod(0o600)

    eval_skill_name = f"{skill_name}-working-tree-eval"
    eval_skill_path = (
        eval_workspace / ".agents" / "skills" / eval_skill_name
    )
    eval_skill_path.parent.mkdir(parents=True)
    shutil.copytree(skill_path, eval_skill_path)

    skill_document = eval_skill_path / "SKILL.md"
    original_document = skill_document.read_text(encoding="utf-8")
    isolated_document = re.sub(
        rf"\A---\nname: {re.escape(skill_name)}\n",
        f"---\nname: {eval_skill_name}\n",
        original_document,
        count=1,
    )
    if isolated_document == original_document:
        raise SystemExit("Unable to isolate working-tree skill frontmatter")
    skill_document.write_text(isolated_document, encoding="utf-8")

    return eval_workspace, eval_codex_home, eval_user_home, eval_skill_name


def read_live_answer(
    entry: dict[str, object],
    case_id: str,
    options: argparse.Namespace,
    eval_workspace: Path,
    eval_codex_home: Path,
    eval_user_home: Path,
    eval_skill_name: str,
) -> tuple[str | None, str | None]:
    prompt = isolated_prompt(entry, eval_skill_name, case_id)
    output_file = tempfile.NamedTemporaryFile(
        prefix=f"{options.skill}-{case_id}",
        suffix=".txt",
        delete=False,
    )
    output_path = Path(output_file.name)
    output_file.close()

    command = [
        options.codex,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--cd",
        str(eval_workspace),
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
    try:
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                env=environment,
                capture_output=True,
                text=True,
                timeout=options.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None, f"timed out after {options.timeout} seconds"

        if completed.returncode != 0:
            diagnostics = "\n".join(
                (completed.stderr + "\n" + completed.stdout).splitlines()[-20:]
            ).strip()
            message = f"Codex exited with status {completed.returncode}"
            if diagnostics:
                message = f"{message}\n{diagnostics}"
            return None, message

        answer = (
            output_path.read_text(encoding="utf-8").strip()
            if output_path.exists()
            else ""
        )
        return answer, None
    finally:
        output_path.unlink(missing_ok=True)


def evaluate_answer(
    answer: str,
    required_patterns: list[re.Pattern[str]],
    forbidden_patterns: list[re.Pattern[str]],
) -> list[str]:
    failures: list[str] = []
    if not answer:
        failures.append("answer is empty")
    for pattern in required_patterns:
        if not pattern.search(answer):
            failures.append(f"missing required pattern {pattern.pattern!r}")
    for pattern in forbidden_patterns:
        if pattern.search(answer):
            failures.append(f"matched forbidden pattern {pattern.pattern!r}")
    return failures


def main() -> int:
    options = parse_args()
    skill_path = find_skill_path(options.skill)
    contract_path = EVALS_DIR / f"{options.skill}.behavior.json"
    if not contract_path.is_file():
        raise SystemExit(f"Behavior contract not found: {contract_path}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["skill"] != options.skill:
        raise SystemExit(
            f"Behavior contract skill does not match --skill {options.skill!r}"
        )
    cases = contract["cases"]

    if options.case_ids:
        known_ids = [entry["id"] for entry in cases]
        unknown_ids = [
            case_id for case_id in options.case_ids if case_id not in known_ids
        ]
        if unknown_ids:
            raise SystemExit(f"Unknown case id(s): {', '.join(unknown_ids)}")
        selected_ids = set(options.case_ids)
        cases = [entry for entry in cases if entry["id"] in selected_ids]

    if options.list:
        for entry in cases:
            assertions = entry["expected"]["assertions"]
            check_count = sum(len(patterns) for patterns in assertions.values())
            print(
                f"{entry['id']}\t{entry['category']}\t"
                f"{entry.get('runner', 'behavior')}\t{check_count} assertion(s)"
            )
        return 0

    workspace_only = [
        entry["id"] for entry in cases if entry.get("runner") == "workspace"
    ]
    if options.case_ids and workspace_only:
        raise SystemExit(
            "Workspace-only case(s) must use run_workspace_evals.py: "
            + ", ".join(workspace_only)
        )
    cases = [entry for entry in cases if entry.get("runner") != "workspace"]

    answers_directory: Path | None = None
    if options.answers is not None:
        answers_directory = (
            options.answers
            if options.answers.is_absolute()
            else ROOT / options.answers
        )
        if not answers_directory.is_dir():
            raise SystemExit(
                f"Saved-answer directory not found: {answers_directory}"
            )
    elif not command_available(options.codex):
        raise SystemExit(f"Codex executable not found: {options.codex}")
    if options.timeout <= 0:
        raise SystemExit("--timeout must be positive")

    temporary_directory: tempfile.TemporaryDirectory[str] | None = None
    if answers_directory is None:
        temporary_directory = tempfile.TemporaryDirectory(
            prefix=f"{options.skill}-eval-"
        )
        (
            eval_workspace,
            eval_codex_home,
            eval_user_home,
            eval_skill_name,
        ) = prepare_isolated_workspace(
            options.skill,
            skill_path,
            Path(temporary_directory.name),
        )

    failed = 0
    try:
        for entry in cases:
            case_id = entry["id"]
            assertions = entry["expected"]["assertions"]
            required_patterns = compile_patterns(
                assertions["required_regex"],
                f"{case_id}.required_regex",
            )
            forbidden_patterns = compile_patterns(
                assertions["forbidden_regex"],
                f"{case_id}.forbidden_regex",
            )
            if answers_directory is not None:
                answer_path = answers_directory / f"{case_id}.txt"
                if not answer_path.is_file():
                    print(
                        f"[FAIL] {case_id}: saved answer is missing: {answer_path}",
                        file=sys.stderr,
                    )
                    failed += 1
                    continue
                answer = answer_path.read_text(encoding="utf-8").strip()
            else:
                answer, execution_error = read_live_answer(
                    entry,
                    case_id,
                    options,
                    eval_workspace,
                    eval_codex_home,
                    eval_user_home,
                    eval_skill_name,
                )
                if execution_error is not None:
                    print(
                        f"[FAIL] {case_id}: {execution_error}",
                        file=sys.stderr,
                    )
                    failed += 1
                    continue
                assert answer is not None

            failures = evaluate_answer(
                answer,
                required_patterns,
                forbidden_patterns,
            )
            if not failures:
                print(f"[PASS] {case_id}")
                if options.show_output:
                    print(answer)
                continue

            print(f"[FAIL] {case_id}", file=sys.stderr)
            for failure in failures:
                print(f"- {failure}", file=sys.stderr)
            print("--- answer ---", file=sys.stderr)
            print(answer, file=sys.stderr)
            failed += 1
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()

    if failed == 0:
        print(f"PASS: {len(cases)} behavior case(s).")
        return 0
    print(
        f"FAIL: {failed} of {len(cases)} behavior case(s) failed.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
