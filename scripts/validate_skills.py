#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LICENSE_PATH = ROOT / "LICENSE"
SKILLS_DIR = ROOT / "skills"
EVALS_DIR = ROOT / "evals"
BEHAVIOR_RUNNER = ROOT / "scripts" / "run_behavior_evals.py"
WORKSPACE_RUNNER = ROOT / "scripts" / "run_workspace_evals.py"
CAPABILITY_MAP_PATH = ROOT / "capabilities" / "map.json"
SKILL_NAME_PATTERN = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "disable-model-invocation"}
ALLOWED_CONTRACT_KEYS = {
    "automated",
    "cases",
    "execution",
    "schema_version",
    "skill",
    "source_assertions",
}
ALLOWED_EXECUTION_KEYS = {"description", "mode", "runner"}
ALLOWED_CASE_KEYS = {"category", "expected", "id", "invocation", "prompt"}
ALLOWED_EXPECTED_KEYS = {"assertions"}
ALLOWED_ASSERTION_KEYS = {"forbidden_regex", "required_regex"}
ALLOWED_CAPABILITY_MAP_KEYS = {"capabilities", "schema_version"}
ALLOWED_CAPABILITY_KEYS = {
    "entrypoint",
    "id",
    "inputs",
    "invocation",
    "kind",
    "safety_boundaries",
    "status",
    "workspace_access",
}
ALLOWED_WORKSPACE_ACCESS_KEYS = {"current", "planned"}
REQUIRED_CASES_BY_SKILL = {
    "bootstrap-project": {
        "new-rust-library": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-rust-cli": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "existing-rust-baseline": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-node-library": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-node-cli": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "existing-node-baseline": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-python-library": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-python-cli": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "existing-python-baseline": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-go-library": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-go-cli": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "existing-go-baseline": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-zig-library": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "new-zig-cli": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "zig-verification-failure": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "existing-zig-baseline": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "existing-zig-planning": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "ambiguous-stack": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "monorepo-target-required": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "tool-migration-conflict": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
    },
    "dsa-design": {
        "prose-edit-no-trigger": {
            "category": "out-of-scope",
            "invocation": "implicit",
        },
        "simple-crud-no-forced-dsa": {
            "category": "applicability-gate",
            "invocation": "implicit",
        },
        "top-k-material-decision": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "delegated-choice-no-pause": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
    },
    "sell-product-in-china": {
        "strategy-only-stage-boundary": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "strategy-deliverable-write": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "full-pack-stage-gates": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "missing-image-tool": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "high-risk-claims-blocked": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "untrusted-markdown-rendering": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "unapproved-publication": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "clothing-out-of-scope": {
            "category": "out-of-scope",
            "invocation": "explicit",
        },
        "unrelated-prose-no-trigger": {
            "category": "out-of-scope",
            "invocation": "implicit",
        },
    },
    "juanjuan-illustrations": {
        "plan-only-shot-list": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "single-concept-identity": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "long-domain-direct-single": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "commercial-rights-boundary": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "precise-architecture-diagram-out-of-scope": {
            "category": "out-of-scope",
            "invocation": "explicit",
        },
    },
    "napi-rs": {
        "out-of-scope-direct-answer": {
            "category": "out-of-scope",
            "invocation": "implicit",
        },
        "generic-binding-design": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "lifetime-and-concurrency": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "unapproved-release": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "coverage-verification": {
            "category": "documentation-integrity",
            "invocation": "explicit",
        },
    },
    "mise": {
        "out-of-scope-direct-answer": {
            "category": "out-of-scope",
            "invocation": "implicit",
        },
        "project-config-design": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "untrusted-config": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "reproducible-ci": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "untrusted-ci-config": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "coverage-verification": {
            "category": "documentation-integrity",
            "invocation": "explicit",
        },
    },
    "zig": {
        "out-of-scope-direct-answer": {
            "category": "out-of-scope",
            "invocation": "implicit",
        },
        "version-aligned-build-change": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "allocator-ownership": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "untrusted-build-script": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "verification-matrix": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "test-step-executes": {
            "category": "test-integrity",
            "invocation": "explicit",
        },
        "dependency-update-boundary": {
            "category": "dependency-management",
            "invocation": "explicit",
        },
        "c-interop-boundary": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "explicit-version-migration": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "measurement-driven-optimization": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "coding-style-review": {
            "category": "positive-trigger",
            "invocation": "explicit",
        },
        "default-latest-stable": {
            "category": "version-routing",
            "invocation": "explicit",
        },
        "supported-version-range": {
            "category": "version-routing",
            "invocation": "explicit",
        },
        "runtime-safety-boundary": {
            "category": "safety-boundary",
            "invocation": "explicit",
        },
        "official-release-verification": {
            "category": "documentation-integrity",
            "invocation": "explicit",
        },
    },
}
MARKDOWN_LINK_PATTERN = re.compile(
    r"""!?\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)"""
    r"""(?:\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?\s*\)"""
)


class SimpleYamlError(ValueError):
    pass


def parse_yaml_scalar(value: str) -> object:
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise SimpleYamlError(str(error)) from error
        if not isinstance(parsed, str):
            raise SimpleYamlError("double-quoted scalar must be a string")
        return parsed
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise SimpleYamlError("unterminated single-quoted scalar")
        return value[1:-1].replace("''", "'")
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        return int(value)
    if not value:
        raise SimpleYamlError("empty scalar")
    if value[0] in "[{&*!|>":
        raise SimpleYamlError(
            "unsupported YAML feature; use nested mappings and scalar values"
        )
    return value


def parse_simple_yaml(source: str) -> object:
    """Parse the small, mapping-only YAML subset used by Skill metadata."""
    meaningful: list[tuple[int, int, str]] = []
    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
            raise SimpleYamlError(f"line {line_number}: tabs are not valid indentation")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            raise SimpleYamlError(
                f"line {line_number}: indentation must use two-space steps"
            )
        meaningful.append((line_number, indent, raw_line.strip()))

    if not meaningful:
        return None
    if len(meaningful) == 1 and ":" not in meaningful[0][2]:
        line_number, indent, scalar = meaningful[0]
        if indent:
            raise SimpleYamlError(f"line {line_number}: unexpected indentation")
        return parse_yaml_scalar(scalar)

    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-2, root)]
    for line_number, indent, content in meaningful:
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack or indent != stack[-1][0] + 2:
            raise SimpleYamlError(f"line {line_number}: unexpected indentation")
        if ":" not in content:
            raise SimpleYamlError(f"line {line_number}: expected key: value")
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            raise SimpleYamlError(f"line {line_number}: invalid mapping key {key!r}")
        parent = stack[-1][1]
        if key in parent:
            raise SimpleYamlError(f"line {line_number}: duplicate key {key!r}")
        if value:
            parent[key] = parse_yaml_scalar(value)
        else:
            child: dict[str, object] = {}
            parent[key] = child
            stack.append((indent, child))
    return root


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_yaml(path: Path, errors: list[str], label: str) -> dict[str, object] | None:
    try:
        parsed = parse_simple_yaml(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{label}: file is missing")
        return None
    except (OSError, UnicodeError, SimpleYamlError) as error:
        errors.append(f"{label}: invalid YAML ({str(error).splitlines()[0]})")
        return None
    if not isinstance(parsed, dict):
        errors.append(f"{label}: expected a YAML mapping")
        return None
    return parsed


def frontmatter_for(path: Path, errors: list[str]) -> dict[str, object] | None:
    label = relative(path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeError) as error:
        errors.append(f"{label}: cannot read Skill document ({error})")
        return None
    if not lines or lines[0].strip() != "---":
        errors.append(f"{label}: missing opening YAML frontmatter delimiter")
        return None
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        errors.append(f"{label}: missing closing YAML frontmatter delimiter")
        return None
    try:
        metadata = parse_simple_yaml("".join(lines[1:closing_index]))
    except SimpleYamlError as error:
        errors.append(
            f"{label}: invalid frontmatter YAML ({str(error).splitlines()[0]})"
        )
        return None
    if not isinstance(metadata, dict):
        errors.append(f"{label}: frontmatter must be a YAML mapping")
        return {}
    return metadata


def local_markdown_targets(path: Path) -> list[tuple[str, int]]:
    targets: list[tuple[str, int]] = []
    fence_character: str | None = None
    fence_length = 0
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if fence_character:
            if re.match(
                rf"^\s*{re.escape(fence_character)}{{{fence_length},}}",
                line,
            ):
                fence_character = None
                fence_length = 0
            continue
        fence = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            fence_character = fence.group(1)[0]
            fence_length = len(fence.group(1))
            continue
        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            raw_target = match.group(1)
            if raw_target.startswith("<") and raw_target.endswith(">"):
                raw_target = raw_target[1:-1]
            if (
                not raw_target
                or raw_target.startswith(("#", "//"))
                or re.match(r"\A[a-z][a-z0-9+.-]*:", raw_target, re.IGNORECASE)
            ):
                continue
            path_part = re.split(r"[?#]", raw_target, maxsplit=1)[0]
            if path_part:
                targets.append((unquote(path_part), line_number))
    return targets


def reject_unexpected_keys(
    mapping: object,
    allowed_keys: set[str],
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(mapping, dict):
        return
    unexpected_keys = set(mapping) - allowed_keys
    if unexpected_keys:
        errors.append(
            f"{label}: unexpected keys: {', '.join(sorted(unexpected_keys))}"
        )


def patterns_for(
    assertions: object,
    label: str,
    errors: list[str],
) -> dict[str, list[re.Pattern[str]]] | None:
    if not isinstance(assertions, dict):
        errors.append(f"{label} must be an object")
        return None
    reject_unexpected_keys(assertions, ALLOWED_ASSERTION_KEYS, label, errors)
    parsed: dict[str, list[re.Pattern[str]]] = {}
    valid = True
    for field in ("required_regex", "forbidden_regex"):
        patterns = assertions.get(field)
        if (
            not isinstance(patterns, list)
            or not patterns
            or any(not isinstance(pattern, str) or not pattern for pattern in patterns)
        ):
            errors.append(
                f"{label}.{field} must be an array of non-empty regular expressions"
            )
            valid = False
            continue
        parsed[field] = []
        for pattern in patterns:
            try:
                parsed[field].append(re.compile(pattern))
            except re.error as error:
                errors.append(
                    f"{label}.{field}: invalid regular expression "
                    f"{pattern!r} ({error})"
                )
                valid = False
    return parsed if valid else None


def bundled_skill_text(skill_dir: Path) -> str:
    sections: list[str] = []
    for path in sorted(item for item in skill_dir.rglob("*") if item.is_file()):
        data = path.read_bytes()
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        sections.append(f"\n--- {path.relative_to(skill_dir)} ---\n{text}")
    return "".join(sections)


def validate_license(errors: list[str]) -> None:
    if not LICENSE_PATH.is_file():
        errors.append("LICENSE: file is missing")
        return
    license_text = LICENSE_PATH.read_text(encoding="utf-8")
    required_markers = (
        "Apache License",
        "Version 2.0, January 2004",
        "END OF TERMS AND CONDITIONS",
    )
    missing = [marker for marker in required_markers if marker not in license_text]
    if missing:
        errors.append(f"LICENSE: missing Apache-2.0 markers: {', '.join(missing)}")


def validate_skills(
    errors: list[str],
) -> tuple[dict[str, Path], set[str], int]:
    skill_files = (
        sorted(path for path in SKILLS_DIR.rglob("SKILL.md") if path.is_file())
        if SKILLS_DIR.is_dir()
        else []
    )
    if not skill_files:
        errors.append("skills/: directory is missing or contains no SKILL.md files")
    skills_by_name: dict[str, Path] = {}
    manual_skills: set[str] = set()

    for skill_file in skill_files:
        skill_dir = skill_file.parent
        directory_name = skill_dir.name
        label = relative(skill_file)
        metadata = frontmatter_for(skill_file, errors)
        if metadata is not None:
            name = metadata.get("name")
            description = metadata.get("description")
            disable_model_invocation = metadata.get(
                "disable-model-invocation",
                False,
            )
            unexpected_keys = set(metadata) - ALLOWED_FRONTMATTER_KEYS
            if unexpected_keys:
                errors.append(
                    f"{label}: unexpected frontmatter keys: "
                    f"{', '.join(sorted(unexpected_keys))}"
                )
            if (
                not isinstance(name, str)
                or not SKILL_NAME_PATTERN.fullmatch(name)
                or len(name) > 64
            ):
                errors.append(
                    f"{label}: name must be a lowercase hyphen-case string "
                    "of at most 64 characters"
                )
            if isinstance(name, str) and name != directory_name:
                errors.append(
                    f"{label}: name {name!r} does not match directory "
                    f"{directory_name!r}"
                )
            if (
                not isinstance(description, str)
                or not description.strip()
                or len(description) > 1024
                or re.search(r"[<>]", description)
            ):
                errors.append(
                    f"{label}: description must be a non-empty string of at most "
                    "1024 characters without angle brackets"
                )
            if not isinstance(disable_model_invocation, bool):
                errors.append(
                    f"{label}: disable-model-invocation must be a boolean"
                )
            if (
                isinstance(name, str)
                and SKILL_NAME_PATTERN.fullmatch(name)
                and name == directory_name
            ):
                previous = skills_by_name.get(name)
                if previous:
                    errors.append(
                        f"{label}: duplicate skill name {name!r}; already used by "
                        f"{relative(previous)}"
                    )
                else:
                    skills_by_name[name] = skill_dir
                    if disable_model_invocation is True:
                        manual_skills.add(name)

        openai_path = skill_dir / "agents" / "openai.yaml"
        openai = load_yaml(openai_path, errors, relative(openai_path))
        if openai is None:
            continue
        interface = openai.get("interface")
        if not isinstance(interface, dict):
            errors.append(f"{relative(openai_path)}: interface must be a mapping")
            interface = {}
        for field in ("display_name", "short_description", "default_prompt"):
            value = interface.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"{relative(openai_path)}: interface.{field} must be "
                    "a non-empty string"
                )
        short_description = interface.get("short_description")
        if isinstance(short_description, str) and not (
            25 <= len(short_description) <= 64
        ):
            errors.append(
                f"{relative(openai_path)}: interface.short_description must "
                "contain 25-64 characters"
            )
        default_prompt = interface.get("default_prompt")
        if isinstance(default_prompt, str) and f"${directory_name}" not in default_prompt:
            errors.append(
                f"{relative(openai_path)}: interface.default_prompt must mention "
                f"${directory_name}"
            )

        policy = openai.get("policy")
        if not isinstance(policy, dict):
            errors.append(f"{relative(openai_path)}: policy must be a mapping")
            policy = {}
        allow_implicit_invocation = policy.get("allow_implicit_invocation")
        if not isinstance(allow_implicit_invocation, bool):
            errors.append(
                f"{relative(openai_path)}: policy.allow_implicit_invocation "
                "must be a boolean"
            )
        elif directory_name in manual_skills and allow_implicit_invocation:
            errors.append(
                f"{relative(openai_path)}: policy.allow_implicit_invocation must "
                "be false when disable-model-invocation is true"
            )
        elif directory_name not in manual_skills and not allow_implicit_invocation:
            errors.append(
                f"{relative(openai_path)}: policy.allow_implicit_invocation must "
                "be true unless disable-model-invocation is true"
            )
    return skills_by_name, manual_skills, len(skill_files)


def string_list(
    value: object,
    label: str,
    errors: list[str],
) -> list[str] | None:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        errors.append(f"{label} must be a non-empty array of non-empty strings")
        return None
    if len(set(value)) != len(value):
        errors.append(f"{label} must not contain duplicates")
    return value


def validate_capability_map(
    skills_by_name: dict[str, Path],
    manual_skills: set[str],
    errors: list[str],
) -> int:
    label = relative(CAPABILITY_MAP_PATH)
    try:
        capability_map: Any = json.loads(
            CAPABILITY_MAP_PATH.read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        errors.append(f"{label}: file is missing")
        return 0
    except json.JSONDecodeError as error:
        errors.append(f"{label}: invalid JSON ({str(error).splitlines()[0]})")
        return 0
    if not isinstance(capability_map, dict):
        errors.append(f"{label}: expected a JSON object")
        return 0
    reject_unexpected_keys(
        capability_map,
        ALLOWED_CAPABILITY_MAP_KEYS,
        label,
        errors,
    )
    if capability_map.get("schema_version") != 1:
        errors.append(f"{label}: schema_version must be 1")
    capabilities = capability_map.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append(f"{label}: capabilities must be an array")
        return 0

    registered_manual_skills: set[str] = set()
    ids: list[str] = []
    for index, capability in enumerate(capabilities):
        capability_label = f"{label}: capabilities[{index}]"
        if not isinstance(capability, dict):
            errors.append(f"{capability_label} must be an object")
            continue
        reject_unexpected_keys(
            capability,
            ALLOWED_CAPABILITY_KEYS,
            capability_label,
            errors,
        )
        capability_id = capability.get("id")
        if not isinstance(capability_id, str) or capability_id not in skills_by_name:
            errors.append(f"{capability_label}.id must name a discovered Skill")
            continue
        ids.append(capability_id)
        expected_entrypoint = relative(skills_by_name[capability_id] / "SKILL.md")
        if capability.get("entrypoint") != expected_entrypoint:
            errors.append(
                f"{capability_label}.entrypoint must be {expected_entrypoint}"
            )
        if capability.get("kind") != "composite":
            errors.append(f'{capability_label}.kind must be "composite"')
        if capability.get("status") != "existing":
            errors.append(f'{capability_label}.status must be "existing"')
        invocation = capability.get("invocation")
        if invocation not in {"manual", "model"}:
            errors.append(
                f'{capability_label}.invocation must be "manual" or "model"'
            )
        if capability_id in manual_skills:
            registered_manual_skills.add(capability_id)
            if invocation != "manual":
                errors.append(
                    f'{capability_label}.invocation must be "manual" for a '
                    "manual Skill"
                )
        string_list(capability.get("inputs"), f"{capability_label}.inputs", errors)
        string_list(
            capability.get("safety_boundaries"),
            f"{capability_label}.safety_boundaries",
            errors,
        )
        workspace_access = capability.get("workspace_access")
        reject_unexpected_keys(
            workspace_access,
            ALLOWED_WORKSPACE_ACCESS_KEYS,
            f"{capability_label}.workspace_access",
            errors,
        )
        if not isinstance(workspace_access, dict):
            errors.append(f"{capability_label}.workspace_access must be an object")
        else:
            if workspace_access.get("current") not in {"read-only", "target-write"}:
                errors.append(
                    f"{capability_label}.workspace_access.current must be "
                    '"read-only" or "target-write"'
                )
            planned = workspace_access.get("planned")
            if not isinstance(planned, str) or not planned.strip():
                errors.append(
                    f"{capability_label}.workspace_access.planned must be "
                    "a non-empty string"
                )

    duplicate_ids = [
        capability_id
        for capability_id, count in Counter(ids).items()
        if count > 1
    ]
    if duplicate_ids:
        errors.append(f"{label}: duplicate capability ids: {', '.join(duplicate_ids)}")
    for skill_name in sorted(manual_skills - registered_manual_skills):
        errors.append(f"{label}: manual Skill {skill_name} must be registered")
    return len(capabilities)


def validate_markdown_links(errors: list[str]) -> tuple[int, int]:
    markdown_files = [ROOT / "README.md"]
    if SKILLS_DIR.is_dir():
        markdown_files.extend(SKILLS_DIR.rglob("*.md"))
    unique_files = sorted({path for path in markdown_files if path.is_file()})
    local_link_count = 0
    for markdown_file in unique_files:
        for target, line_number in local_markdown_targets(markdown_file):
            local_link_count += 1
            resolved = (markdown_file.parent / target).resolve()
            source = relative(markdown_file)
            if resolved != ROOT and ROOT not in resolved.parents:
                errors.append(
                    f"{source}:{line_number}: local link escapes the repository: "
                    f"{target}"
                )
                continue
            if not resolved.exists():
                errors.append(
                    f"{source}:{line_number}: missing local link target: {target}"
                )
    return len(unique_files), local_link_count


def validate_contracts(
    skills_by_name: dict[str, Path],
    manual_skills: set[str],
    errors: list[str],
) -> int:
    contracts = (
        sorted(path for path in EVALS_DIR.glob("*.behavior.json") if path.is_file())
        if EVALS_DIR.is_dir()
        else []
    )
    if not contracts:
        errors.append("evals/: no behavior contracts found")
    if not BEHAVIOR_RUNNER.is_file():
        errors.append(f"{relative(BEHAVIOR_RUNNER)}: file is missing")

    for contract_path in contracts:
        label = relative(contract_path)
        try:
            contract: Any = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            errors.append(f"{label}: invalid JSON ({str(error).splitlines()[0]})")
            continue
        if not isinstance(contract, dict):
            errors.append(f"{label}: expected a JSON object")
            continue
        reject_unexpected_keys(contract, ALLOWED_CONTRACT_KEYS, label, errors)
        schema_version = contract.get("schema_version")
        if isinstance(schema_version, bool) or schema_version != 1:
            errors.append(f"{label}: schema_version must be 1")
        if contract.get("automated") is not True:
            errors.append(f"{label}: automated must be true")

        skill_name = contract.get("skill")
        if not isinstance(skill_name, str) or skill_name not in skills_by_name:
            errors.append(f"{label}: skill must name a discovered Skill")
            skill_name = None
        if skill_name and contract_path.name != f"{skill_name}.behavior.json":
            errors.append(
                f"{label}: file name must be {skill_name}.behavior.json"
            )

        source_patterns = patterns_for(
            contract.get("source_assertions"),
            f"{label}: source_assertions",
            errors,
        )
        if source_patterns and skill_name:
            skill_dir = skills_by_name[skill_name]
            skill_document = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            bundled_text = bundled_skill_text(skill_dir)
            for pattern in source_patterns["required_regex"]:
                if not pattern.search(skill_document):
                    errors.append(
                        f"{label}: Skill source is missing required pattern "
                        f"{pattern.pattern!r}"
                    )
            for pattern in source_patterns["forbidden_regex"]:
                if pattern.search(bundled_text):
                    errors.append(
                        f"{label}: Skill source matches forbidden pattern "
                        f"{pattern.pattern!r}"
                    )

        execution = contract.get("execution")
        reject_unexpected_keys(
            execution,
            ALLOWED_EXECUTION_KEYS,
            f"{label}: execution",
            errors,
        )
        if not isinstance(execution, dict) or execution.get("mode") != "codex-cli":
            errors.append(f'{label}: execution.mode must be "codex-cli"')
        if (
            not isinstance(execution, dict)
            or execution.get("runner") != relative(BEHAVIOR_RUNNER)
        ):
            errors.append(
                f"{label}: execution.runner must reference the repository "
                "behavior runner"
            )
        if (
            not isinstance(execution, dict)
            or not isinstance(execution.get("description"), str)
            or not execution["description"].strip()
        ):
            errors.append(
                f"{label}: execution.description must be a non-empty string"
            )

        cases = contract.get("cases")
        if not isinstance(cases, list) or not cases:
            errors.append(f"{label}: cases must be a non-empty array")
            continue
        case_ids = [
            entry["id"]
            for entry in cases
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        ]
        duplicates = [
            case_id
            for case_id, count in Counter(case_ids).items()
            if count > 1
        ]
        if duplicates:
            errors.append(f"{label}: duplicate case ids: {', '.join(duplicates)}")

        required_cases = REQUIRED_CASES_BY_SKILL.get(skill_name)
        if required_cases is None:
            errors.append(
                f"{label}: required case schema is not configured for "
                f"{skill_name!r}"
            )
            required_cases = {}
        missing_case_ids = [
            case_id for case_id in required_cases if case_id not in case_ids
        ]
        if missing_case_ids:
            errors.append(
                f"{label}: missing required cases: {', '.join(missing_case_ids)}"
            )
        cases_by_id = {
            entry["id"]: entry
            for entry in cases
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        for case_id, expected_fields in required_cases.items():
            entry = cases_by_id.get(case_id)
            if entry is None:
                continue
            for field, expected_value in expected_fields.items():
                if entry.get(field) != expected_value:
                    errors.append(
                        f"{label}: {case_id} {field} must be {expected_value}"
                    )

        for index, entry in enumerate(cases):
            case_label = f"{label}: cases[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{case_label} must be an object")
                continue
            reject_unexpected_keys(
                entry,
                ALLOWED_CASE_KEYS,
                case_label,
                errors,
            )
            case_id = entry.get("id")
            if not isinstance(case_id, str) or not case_id:
                errors.append(f"{case_label}.id must be a non-empty string")
            category = entry.get("category")
            if not isinstance(category, str) or not category.strip():
                errors.append(f"{case_label}.category must be a non-empty string")
            prompt = entry.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                errors.append(f"{case_label}.prompt must be a non-empty string")
            invocation = entry.get("invocation")
            if invocation not in {"explicit", "implicit"}:
                errors.append(
                    f'{case_label}.invocation must be "explicit" or "implicit"'
                )
            elif skill_name in manual_skills and invocation == "implicit":
                errors.append(
                    f"{label}: manual Skill {skill_name} cannot define implicit "
                    "behavior cases"
                )
            if skill_name and isinstance(case_id, str) and case_id:
                fixture_path = (
                    EVALS_DIR / "fixtures" / skill_name / f"{case_id}.txt"
                )
                if (
                    not fixture_path.is_file()
                    or not fixture_path.read_text(encoding="utf-8").strip()
                ):
                    errors.append(
                        f"{relative(fixture_path)}: saved answer must exist "
                        "and be non-empty"
                    )

            expected = entry.get("expected")
            if not isinstance(expected, dict):
                errors.append(f"{case_label}.expected must be an object")
                continue
            reject_unexpected_keys(
                expected,
                ALLOWED_EXPECTED_KEYS,
                f"{case_label}.expected",
                errors,
            )
            patterns_for(
                expected.get("assertions"),
                f"{case_label}.expected.assertions",
                errors,
            )
    return len(contracts)


def main() -> int:
    errors: list[str] = []
    validate_license(errors)
    skills_by_name, manual_skills, skill_count = validate_skills(errors)
    markdown_count, local_link_count = validate_markdown_links(errors)
    capability_count = validate_capability_map(
        skills_by_name,
        manual_skills,
        errors,
    )
    contract_count = validate_contracts(skills_by_name, manual_skills, errors)
    if not WORKSPACE_RUNNER.is_file():
        errors.append(f"{relative(WORKSPACE_RUNNER)}: file is missing")

    if not errors:
        print(
            f"PASS: validated {skill_count} skill(s), "
            f"{markdown_count} Markdown file(s), "
            f"{local_link_count} local link(s), and "
            f"{contract_count} behavior contract(s), with "
            f"{capability_count} registered capability item(s)."
        )
        return 0
    print(
        f"FAIL: found {len(errors)} validation error(s):",
        file=sys.stderr,
    )
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
