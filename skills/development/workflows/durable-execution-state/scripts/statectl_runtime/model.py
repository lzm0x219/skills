from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .codec import (
    canonical_json as json_text,
    json_size,
    validate_rfc3339 as validate_timestamp,
)
from .errors import StateError


SCHEMA_VERSION = 1
DEFAULT_MAX_STATE_BYTES = 64 * 1024
MAX_EVENT_PAYLOAD_BYTES = 64 * 1024
STATE_KEYS = {
    "schema_version",
    "state_version",
    "task",
    "constraints",
    "confirmed_facts",
    "hypotheses",
    "plan",
    "pending_actions",
    "failed_attempts",
    "blockers",
    "completion_evidence",
    "evidence_refs",
    "artifact_refs",
}
PATCHABLE_ROOTS = {
    "confirmed_facts",
    "hypotheses",
    "plan",
    "failed_attempts",
    "blockers",
    "completion_evidence",
    "evidence_refs",
    "artifact_refs",
}
ACTION_KEYS = {
    "idempotency_key",
    "tool",
    "args",
    "preconditions",
    "authorization_ref",
}
RECEIPT_KEYS = {
    "status",
    "idempotency_key",
    "source_ref",
    "observed_at",
    "details",
}
PATCH_OPERATIONS = {"add", "replace", "remove"}
PRECONDITION_OPERATORS = {"exists", "absent", "equals", "not_equals"}
RECEIPT_STATUSES = {"succeeded", "failed", "partial", "unknown"}
ACTION_OUTCOMES = {"pending", "confirmed", "failed"}
OUTCOME_RECEIPT_STATUSES = {
    "pending": {"partial", "unknown"},
    "confirmed": {"succeeded"},
    "failed": {"failed"},
}
MISSING = object()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_bounded_payload(value: object, label: str) -> None:
    size = json_size(value)
    if size > MAX_EVENT_PAYLOAD_BYTES:
        raise StateError(
            f"{label} size {size} exceeds limit {MAX_EVENT_PAYLOAD_BYTES} bytes; "
            "store large content externally and pass a stable reference"
        )


def load_json(path: Path, expected_type: type[Any]) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise StateError(f"JSON file does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise StateError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(value, expected_type):
        raise StateError(f"{path} must contain a {expected_type.__name__}")
    return value


def validate_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"{label} must be a non-empty string")
    return value


def validate_criteria(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise StateError("completion criteria must be a non-empty array")
    criteria: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, entry in enumerate(value):
        if not isinstance(entry, dict) or set(entry) != {"id", "description"}:
            raise StateError(
                f"completion criteria[{index}] must contain only id and description"
            )
        criterion_id = validate_non_empty_string(entry["id"], f"criteria[{index}].id")
        description = validate_non_empty_string(
            entry["description"], f"criteria[{index}].description"
        )
        if criterion_id in ids:
            raise StateError(f"duplicate completion criterion id: {criterion_id}")
        ids.add(criterion_id)
        criteria.append({"id": criterion_id, "description": description})
    return criteria


def validate_state(state: dict[str, Any], max_state_bytes: int) -> None:
    if set(state) != STATE_KEYS:
        missing = sorted(STATE_KEYS - set(state))
        extra = sorted(set(state) - STATE_KEYS)
        raise StateError(f"state keys mismatch; missing={missing}, extra={extra}")
    if state["schema_version"] != SCHEMA_VERSION:
        raise StateError(f"schema_version must be {SCHEMA_VERSION}")
    if isinstance(state["state_version"], bool) or not isinstance(
        state["state_version"], int
    ):
        raise StateError("state_version must be an integer")
    if state["state_version"] < 0:
        raise StateError("state_version must not be negative")
    task = state["task"]
    if not isinstance(task, dict) or set(task) != {
        "id",
        "objective",
        "completion_criteria",
        "status",
    }:
        raise StateError("task must contain only id, objective, completion_criteria, status")
    validate_non_empty_string(task["id"], "task.id")
    validate_non_empty_string(task["objective"], "task.objective")
    validate_criteria(task["completion_criteria"])
    if task["status"] not in {"active", "complete"}:
        raise StateError("task.status must be active or complete")
    if not isinstance(state["constraints"], list) or any(
        not isinstance(item, str) or not item.strip() for item in state["constraints"]
    ):
        raise StateError("constraints must be an array of non-empty strings")
    for key in STATE_KEYS - {
        "schema_version",
        "state_version",
        "task",
        "constraints",
    }:
        if not isinstance(state[key], dict):
            raise StateError(f"{key} must be an object")
    criterion_ids = {entry["id"] for entry in task["completion_criteria"]}
    unknown_evidence = set(state["completion_evidence"]) - criterion_ids
    if unknown_evidence:
        raise StateError(
            "completion_evidence contains unknown criteria: "
            + ", ".join(sorted(unknown_evidence))
        )
    for criterion_id, evidence in state["completion_evidence"].items():
        if not isinstance(evidence, dict) or set(evidence) != {
            "source_ref",
            "observed_at",
        }:
            raise StateError(
                f"completion evidence for {criterion_id} must contain only "
                "source_ref and observed_at"
            )
        validate_non_empty_string(
            evidence.get("source_ref"),
            f"completion_evidence.{criterion_id}.source_ref",
        )
        validate_timestamp(
            evidence.get("observed_at"),
            f"completion_evidence.{criterion_id}.observed_at",
        )
    for fact_id, fact in state["confirmed_facts"].items():
        allowed_keys = {"value", "source_ref", "observed_at", "fresh_until"}
        if (
            not isinstance(fact, dict)
            or not {"value", "source_ref", "observed_at"} <= set(fact)
            or not set(fact) <= allowed_keys
        ):
            raise StateError(
                f"confirmed fact {fact_id} must contain value, source_ref, "
                "observed_at, and optional fresh_until"
            )
        validate_non_empty_string(
            fact["source_ref"], f"confirmed_facts.{fact_id}.source_ref"
        )
        validate_timestamp(
            fact["observed_at"], f"confirmed_facts.{fact_id}.observed_at"
        )
        if "fresh_until" in fact:
            validate_timestamp(
                fact["fresh_until"], f"confirmed_facts.{fact_id}.fresh_until"
            )
    size = json_size(state)
    if size > max_state_bytes:
        raise StateError(f"state size {size} exceeds limit {max_state_bytes} bytes")


def pointer_parts(path: object, *, require_patchable: bool = True) -> list[str]:
    if not isinstance(path, str) or not path.startswith("/") or path == "/":
        raise StateError("patch path must be a non-root JSON Pointer")
    parts: list[str] = []
    for raw in path[1:].split("/"):
        index = 0
        while index < len(raw):
            if raw[index] == "~" and (
                index + 1 >= len(raw) or raw[index + 1] not in {"0", "1"}
            ):
                raise StateError(f"invalid JSON Pointer escape in {path}")
            index += 2 if raw[index] == "~" else 1
        parts.append(raw.replace("~1", "/").replace("~0", "~"))
    if any(not part for part in parts):
        raise StateError(f"JSON Pointer path segments must be non-empty: {path}")
    if require_patchable and parts[0] not in PATCHABLE_ROOTS:
        raise StateError(f"patch path is protected: {path}")
    if require_patchable and len(parts) == 1:
        raise StateError(f"patch cannot replace an entire state collection: {path}")
    return parts


def parse_list_index(value: str) -> int:
    if not value.isdigit() or (len(value) > 1 and value.startswith("0")):
        raise StateError(f"invalid list index: {value}")
    return int(value)


def value_at_pointer(document: object, path: object) -> object:
    current = document
    for part in pointer_parts(path, require_patchable=False):
        if isinstance(current, dict):
            if part not in current:
                return MISSING
            current = current[part]
        elif isinstance(current, list):
            list_index = parse_list_index(part)
            if list_index >= len(current):
                return MISSING
            current = current[list_index]
        else:
            return MISSING
    return current


def parent_for(document: object, parts: list[str]) -> tuple[object, str]:
    current = document
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                raise StateError(f"patch parent does not exist: {part}")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[parse_list_index(part)]
            except IndexError as error:
                raise StateError(f"invalid list index in patch: {part}") from error
        else:
            raise StateError("patch traverses a scalar value")
    return current, parts[-1]


def apply_patch_operations(
    state: dict[str, Any], operations: list[object]
) -> dict[str, Any]:
    if not operations:
        raise StateError("patch must contain at least one operation")
    result = deepcopy(state)
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise StateError(f"patch[{index}] must be an object")
        op = operation.get("op")
        if op not in PATCH_OPERATIONS:
            raise StateError(f"patch[{index}].op must be add, replace, or remove")
        allowed = {"op", "path"} if op == "remove" else {"op", "path", "value"}
        if set(operation) != allowed:
            raise StateError(f"patch[{index}] has invalid keys for {op}")
        parts = pointer_parts(operation.get("path"))
        parent, leaf = parent_for(result, parts)
        if isinstance(parent, dict):
            exists = leaf in parent
            if op == "add":
                if exists:
                    raise StateError(f"add target already exists: {operation['path']}")
                parent[leaf] = deepcopy(operation["value"])
            elif op == "replace":
                if not exists:
                    raise StateError(f"replace target does not exist: {operation['path']}")
                parent[leaf] = deepcopy(operation["value"])
            else:
                if not exists:
                    raise StateError(f"remove target does not exist: {operation['path']}")
                del parent[leaf]
        elif isinstance(parent, list):
            if leaf == "-" and op == "add":
                parent.append(deepcopy(operation["value"]))
                continue
            list_index = parse_list_index(leaf)
            if op == "add":
                if list_index < 0 or list_index > len(parent):
                    raise StateError(f"list add index out of range: {leaf}")
                parent.insert(list_index, deepcopy(operation["value"]))
            elif 0 <= list_index < len(parent):
                if op == "replace":
                    parent[list_index] = deepcopy(operation["value"])
                else:
                    del parent[list_index]
            else:
                raise StateError(f"list index out of range: {leaf}")
        else:
            raise StateError("patch target parent is a scalar value")
    return result


def validate_preconditions(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise StateError("action.preconditions must be an array")
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise StateError(f"action.preconditions[{index}] must be an object")
        operator = entry.get("operator")
        if operator not in PRECONDITION_OPERATORS:
            raise StateError(
                f"action.preconditions[{index}].operator must be one of "
                f"{sorted(PRECONDITION_OPERATORS)}"
            )
        expected_keys = (
            {"path", "operator", "value"}
            if operator in {"equals", "not_equals"}
            else {"path", "operator"}
        )
        if set(entry) != expected_keys:
            raise StateError(
                f"action.preconditions[{index}] has invalid keys for {operator}"
            )
        pointer_parts(entry.get("path"), require_patchable=False)
        validated.append(entry)
    return validated


def evaluate_preconditions(
    state: dict[str, Any], preconditions: list[dict[str, Any]]
) -> None:
    for index, condition in enumerate(preconditions):
        actual = value_at_pointer(state, condition["path"])
        operator = condition["operator"]
        satisfied = (
            (operator == "exists" and actual is not MISSING)
            or (operator == "absent" and actual is MISSING)
            or (
                operator == "equals"
                and actual is not MISSING
                and actual == condition["value"]
            )
            or (
                operator == "not_equals"
                and actual is not MISSING
                and actual != condition["value"]
            )
        )
        if not satisfied:
            rendered = "<missing>" if actual is MISSING else json_text(actual)
            raise StateError(
                f"action precondition[{index}] failed at {condition['path']}; "
                f"operator={operator}, actual={rendered}"
            )


def require_active(state: dict[str, Any]) -> None:
    if state["task"]["status"] != "active":
        raise StateError("task is complete and cannot be mutated")


def validate_action(value: dict[str, Any]) -> dict[str, Any]:
    if set(value) != ACTION_KEYS:
        raise StateError(f"action keys must be {sorted(ACTION_KEYS)}")
    validate_non_empty_string(value["idempotency_key"], "idempotency_key")
    validate_non_empty_string(value["tool"], "tool")
    validate_non_empty_string(value["authorization_ref"], "authorization_ref")
    if not isinstance(value["args"], dict):
        raise StateError("action.args must be an object")
    value["preconditions"] = validate_preconditions(value["preconditions"])
    require_bounded_payload(value, "action request")
    return value


def pending_action_record(
    request: dict[str, Any],
    started_at: str,
    authorization_verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "idempotency_key": request["idempotency_key"],
        "tool": request["tool"],
        "preconditions": request["preconditions"],
        "authorization_ref": request["authorization_ref"],
        "started_at": started_at,
    }
    if authorization_verification is not None:
        record["authorization_verification"] = authorization_verification
    return record


def validate_receipt(value: dict[str, Any]) -> dict[str, Any]:
    if set(value) != RECEIPT_KEYS:
        raise StateError(f"receipt keys must be {sorted(RECEIPT_KEYS)}")
    if value["status"] not in RECEIPT_STATUSES:
        raise StateError("receipt.status is invalid")
    validate_non_empty_string(value["idempotency_key"], "receipt.idempotency_key")
    validate_non_empty_string(value["source_ref"], "receipt.source_ref")
    validate_timestamp(value["observed_at"], "receipt.observed_at")
    if not isinstance(value["details"], dict):
        raise StateError("receipt.details must be an object")
    require_bounded_payload(value, "action receipt")
    return value


def apply_action_resolution(
    state: dict[str, Any],
    action_id: str,
    outcome: str,
    receipt: dict[str, Any],
    operations: list[object],
) -> dict[str, Any]:
    if action_id not in state["pending_actions"]:
        raise StateError(f"action is not pending: {action_id}")
    pending = state["pending_actions"][action_id]
    if receipt["idempotency_key"] != pending["idempotency_key"]:
        raise StateError("receipt idempotency key does not match the action")
    if receipt["status"] not in OUTCOME_RECEIPT_STATUSES[outcome]:
        raise StateError(
            f"{outcome} outcome requires receipt.status in "
            f"{sorted(OUTCOME_RECEIPT_STATUSES[outcome])}"
        )
    if operations:
        state = apply_patch_operations(state, operations)
        pending = state["pending_actions"][action_id]
    if outcome == "pending":
        pending["last_observation"] = {
            "status": receipt["status"],
            "source_ref": receipt["source_ref"],
            "observed_at": receipt["observed_at"],
        }
        return state
    del state["pending_actions"][action_id]
    if outcome == "failed":
        idempotency_key = pending["idempotency_key"]
        state["failed_attempts"][idempotency_key] = {
            "action_id": action_id,
            "idempotency_key": idempotency_key,
            "tool": pending["tool"],
            "source_ref": receipt["source_ref"],
            "observed_at": receipt["observed_at"],
        }
    return state


def require_completion_ready(state: dict[str, Any]) -> None:
    if state["pending_actions"]:
        raise StateError("cannot complete with pending actions")
    if state["blockers"]:
        raise StateError("cannot complete with unresolved blockers")
    criteria = {entry["id"] for entry in state["task"]["completion_criteria"]}
    missing = sorted(criteria - set(state["completion_evidence"]))
    if missing:
        raise StateError("cannot complete without evidence for: " + ", ".join(missing))
