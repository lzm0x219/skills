from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from .authorization import validate_recorded_authorization
from .errors import StateError
from .model import (
    apply_action_resolution,
    apply_patch_operations,
    evaluate_preconditions,
    json_size,
    json_text,
    load_json,
    pending_action_record,
    require_active,
    require_completion_ready,
    validate_action,
    validate_non_empty_string,
    validate_receipt,
    validate_state,
)
from .store import (
    ActionsRepository,
    SNAPSHOT_NAME,
    connect,
    run_read_transaction,
    state_from_row,
    task_row,
    write_snapshot,
)


def advance_replayed_state(
    state: dict[str, Any], payload: dict[str, Any], max_state_bytes: int
) -> None:
    expected_version = state["state_version"] + 1
    if payload.get("state_version") != expected_version:
        raise StateError(
            "event state versions are not contiguous; "
            f"expected {expected_version}, found {payload.get('state_version')}"
        )
    state["state_version"] = expected_version
    validate_state(state, max_state_bytes)


def replay_events(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], int, str]:
    event_cursor = connection.execute(
        "SELECT sequence, kind, payload_json FROM events "
        "WHERE task_id = ? ORDER BY sequence",
        (row["task_id"],),
    )
    events = iter(event_cursor)
    initialized = next(events, None)
    if initialized is None or initialized["kind"] != "initialized":
        raise StateError("event ledger must begin with initialized")
    initial = json.loads(initialized["payload_json"])
    if not isinstance(initial, dict):
        raise StateError("initialized event payload must be a state object")
    state = deepcopy(initial)
    validate_state(state, row["max_state_bytes"])
    if state["state_version"] != 0:
        raise StateError("initialized event must use state_version 0")
    actions: dict[str, dict[str, Any]] = {}
    event_count = 1

    for event in events:
        event_count += 1
        payload = json.loads(event["payload_json"])
        if not isinstance(payload, dict):
            raise StateError(f"event {event['sequence']} payload must be an object")
        kind = event["kind"]
        require_active(state)
        if kind == "patch-applied":
            operations = payload.get("operations")
            if not isinstance(operations, list):
                raise StateError("patch-applied event operations must be an array")
            state = apply_patch_operations(state, operations)
        elif kind == "action-begun":
            action_id = validate_non_empty_string(
                payload.get("action_id"), "action-begun.action_id"
            )
            request = payload.get("request")
            if not isinstance(request, dict):
                raise StateError("action-begun request must be an object")
            request = validate_action(request)
            evaluate_preconditions(state, request["preconditions"])
            if action_id in actions:
                raise StateError(f"duplicate action id in event ledger: {action_id}")
            if any(
                action["idempotency_key"] == request["idempotency_key"]
                for action in actions.values()
            ):
                raise StateError("duplicate action idempotency key in event ledger")
            started_at = validate_non_empty_string(
                payload.get("started_at"), "action-begun.started_at"
            )
            authorization_verification = payload.get("authorization_verification")
            if authorization_verification is not None:
                authorization_verification = validate_recorded_authorization(
                    authorization_verification,
                    request,
                )
            state["pending_actions"][action_id] = pending_action_record(
                request,
                started_at,
                authorization_verification,
            )
            actions[action_id] = {
                "task_id": row["task_id"],
                "idempotency_key": request["idempotency_key"],
                "status": "pending",
                "request_json": json_text(request),
                "receipt_json": None,
                "resolution_json": None,
            }
        elif kind in {"action-observed", "action-resolved"}:
            action_id = validate_non_empty_string(
                payload.get("action_id"), f"{kind}.action_id"
            )
            if action_id not in state["pending_actions"]:
                raise StateError(f"event resolves non-pending action: {action_id}")
            receipt = payload.get("receipt")
            if not isinstance(receipt, dict):
                raise StateError(f"{kind} receipt must be an object")
            receipt = validate_receipt(receipt)
            operations = payload.get("operations")
            if not isinstance(operations, list):
                raise StateError(f"{kind} operations must be an array")
            outcome = payload.get("outcome")
            if kind == "action-observed":
                if outcome != "pending":
                    raise StateError(
                        "action-observed must keep a partial/unknown action pending"
                    )
            elif outcome not in {"confirmed", "failed"}:
                raise StateError("action-resolved outcome and receipt disagree")
            state = apply_action_resolution(
                state, action_id, outcome, receipt, operations
            )
            resolution = {
                "outcome": outcome,
                "receipt": receipt,
                "operations": operations,
            }
            action = actions.get(action_id)
            if action is None:
                raise StateError("resolved action has no matching begin event")
            action["status"] = "pending" if outcome == "pending" else outcome
            action["receipt_json"] = json_text(receipt)
            action["resolution_json"] = json_text(resolution)
        elif kind == "completed":
            require_completion_ready(state)
            if payload.get("completion_evidence") != state["completion_evidence"]:
                raise StateError("completed event evidence differs from replayed state")
            state["task"]["status"] = "complete"
        else:
            raise StateError(f"unknown event kind: {kind}")
        advance_replayed_state(state, payload, row["max_state_bytes"])

    digest = hashlib.sha256(json_text(state).encode("utf-8")).hexdigest()
    return state, actions, event_count, digest


def replay_store(store: Path) -> dict[str, Any]:
    connection = connect(store)
    try:
        def replay() -> dict[str, Any]:
            row = task_row(connection)
            replayed, _, event_count, state_digest = replay_events(connection, row)
            if replayed != state_from_row(row):
                raise StateError("event replay differs from current state")
            return {
                "task_id": row["task_id"],
                "state_version": replayed["state_version"],
                "event_count": event_count,
                "state_size_bytes": json_size(replayed),
                "state_sha256": state_digest,
                "replayed": True,
            }

        return run_read_transaction(connection, replay)
    finally:
        connection.close()


def verify_store(store: Path) -> dict[str, Any]:
    connection = connect(store)
    try:
        def verify() -> tuple[dict[str, Any], dict[str, Any], bool]:
            row = task_row(connection)
            state = state_from_row(row)
            validate_state(state, row["max_state_bytes"])
            if state["state_version"] != row["state_version"]:
                raise StateError("database and state JSON versions differ")
            if state["task"]["status"] != row["status"]:
                raise StateError("database and state JSON statuses differ")
            replayed, expected_actions, event_count, state_digest = replay_events(
                connection, row
            )
            if replayed != state:
                raise StateError("event replay differs from current state")
            action_rows = ActionsRepository(connection).iter_all()
            actual_actions = {
                action["action_id"]: {
                    "task_id": action["task_id"],
                    "idempotency_key": action["idempotency_key"],
                    "status": action["status"],
                    "request_json": action["request_json"],
                    "receipt_json": action["receipt_json"],
                    "resolution_json": action["resolution_json"],
                }
                for action in action_rows
            }
            if actual_actions != expected_actions:
                raise StateError("action table differs from event replay")
            pending_ids = {
                action_id
                for action_id, action in actual_actions.items()
                if action["status"] == "pending"
            }
            if pending_ids != set(state["pending_actions"]):
                raise StateError("database and state pending actions differ")
            snapshot_path = store / SNAPSHOT_NAME
            snapshot_matches = False
            if snapshot_path.is_file():
                try:
                    snapshot_matches = load_json(snapshot_path, dict) == state
                except StateError:
                    snapshot_matches = False
            result = {
                "task_id": row["task_id"],
                "state_version": row["state_version"],
                "status": row["status"],
                "pending_actions": len(pending_ids),
                "scope": "internal-store",
                "event_count": event_count,
                "state_size_bytes": json_size(state),
                "state_sha256": state_digest,
                "verified": True,
            }
            return result, state, snapshot_matches

        result, state, snapshot_matches = run_read_transaction(connection, verify)
        if not snapshot_matches:
            write_snapshot(store, state)
        return result
    finally:
        connection.close()
