from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any
from uuid import uuid4

from .authorization import verify_authorization
from .errors import StateError
from .model import (
    ACTION_OUTCOMES,
    DEFAULT_MAX_STATE_BYTES,
    OUTCOME_RECEIPT_STATUSES,
    SCHEMA_VERSION,
    apply_action_resolution,
    apply_patch_operations,
    evaluate_preconditions,
    json_size,
    json_text,
    load_json,
    now,
    pending_action_record,
    require_active,
    require_bounded_payload,
    require_completion_ready,
    validate_action,
    validate_criteria,
    validate_non_empty_string,
    validate_receipt,
    validate_state,
)
from .replay import replay_store, verify_store
from .store import (
    ActionsRepository,
    append_event,
    connect,
    create_tables,
    refresh_snapshot_after_commit,
    require_version,
    run_transaction,
    state_from_row,
    task_row,
    update_task,
)


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    criteria = validate_criteria(load_json(Path(args.criteria_file), list))
    constraints: list[str] = []
    if args.constraints_file:
        value = load_json(Path(args.constraints_file), list)
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise StateError("constraints file must contain non-empty strings")
        constraints = value
    connection = connect(store, create=True)
    try:
        create_tables(connection)
        if connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]:
            raise StateError(f"state store is already initialized: {store}")
        state: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "state_version": 0,
            "task": {
                "id": validate_non_empty_string(args.task_id, "task id"),
                "objective": validate_non_empty_string(args.objective, "objective"),
                "completion_criteria": criteria,
                "status": "active",
            },
            "constraints": constraints,
            "confirmed_facts": {},
            "hypotheses": {},
            "plan": {},
            "pending_actions": {},
            "failed_attempts": {},
            "blockers": {},
            "completion_evidence": {},
            "evidence_refs": {},
            "artifact_refs": {},
        }
        validate_state(state, args.max_state_bytes)

        def initialize() -> dict[str, Any]:
            timestamp = now()
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, schema_version, state_version, status, state_json,
                    max_state_bytes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state["task"]["id"],
                    SCHEMA_VERSION,
                    0,
                    "active",
                    json_text(state),
                    args.max_state_bytes,
                    timestamp,
                    timestamp,
                ),
            )
            append_event(connection, state["task"]["id"], "initialized", state)
            return state

        state = run_transaction(connection, "init", initialize)
        refresh_snapshot_after_commit(store, state)
        return state
    finally:
        connection.close()


def command_show(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    connection = connect(store)
    try:
        row = task_row(connection)
        state = state_from_row(row)
        validate_state(state, row["max_state_bytes"])
        refresh_snapshot_after_commit(store, state)
        return state
    finally:
        connection.close()


def validated_patch_candidate(
    row: sqlite3.Row,
    expected_version: int,
    operations: list[object],
) -> dict[str, Any]:
    require_version(row, expected_version)
    state = state_from_row(row)
    require_active(state)
    require_bounded_payload(operations, "patch")
    candidate = apply_patch_operations(state, operations)
    candidate["state_version"] = row["state_version"] + 1
    validate_state(candidate, row["max_state_bytes"])
    return candidate


def command_validate_patch(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    operations = load_json(Path(args.patch_file), list)
    connection = connect(store)
    try:
        row = task_row(connection)
        candidate = validated_patch_candidate(row, args.expected_version, operations)
        return {
            "valid": True,
            "state_version": row["state_version"],
            "candidate_state_version": row["state_version"] + 1,
            "operation_count": len(operations),
            "candidate_size_bytes": json_size(candidate),
        }
    finally:
        connection.close()


def command_apply_patch(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    operations = load_json(Path(args.patch_file), list)
    connection = connect(store)
    try:

        def apply() -> dict[str, Any]:
            row = task_row(connection)
            state = validated_patch_candidate(row, args.expected_version, operations)
            state = update_task(connection, row, state)
            append_event(
                connection,
                row["task_id"],
                "patch-applied",
                {"operations": operations, "state_version": state["state_version"]},
            )
            return state

        state = run_transaction(connection, "apply-patch", apply)
        refresh_snapshot_after_commit(store, state)
        return state
    finally:
        connection.close()


def command_begin_action(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    request = validate_action(load_json(Path(args.action_file), dict))
    request_text = json_text(request)
    connection = connect(store)
    try:
        actions = ActionsRepository(connection)

        def reuse_existing() -> dict[str, Any] | None:
            existing = actions.find_by_idempotency_key(request["idempotency_key"])
            if not existing:
                return None
            if existing["request_json"] != request_text:
                raise StateError("idempotency key is already bound to another request")
            row = task_row(connection)
            return {
                "action_id": existing["action_id"],
                "status": existing["status"],
                "state_version": row["state_version"],
                "reused": True,
            }

        reused = reuse_existing()
        if reused is not None:
            return reused

        authorization_verification = verify_authorization(
            request,
            store=store,
            verifier_path=args.authorization_verifier,
            allow_reference=args.allow_reference_authorization,
        )
        if authorization_verification["mode"] == "reference-only":
            print(
                "WARNING: reference-only authorization does not authorize external "
                "execution; use it only to record a non-executing rehearsal or test",
                file=sys.stderr,
            )
        require_bounded_payload(
            authorization_verification, "authorization verification"
        )

        def begin() -> dict[str, Any]:
            reused = reuse_existing()
            if reused is not None:
                return reused
            row = task_row(connection)
            require_version(row, args.expected_version)
            state = state_from_row(row)
            require_active(state)
            evaluate_preconditions(state, request["preconditions"])
            action_id = str(uuid4())
            timestamp = now()
            actions.insert_pending(
                action_id=action_id,
                task_id=row["task_id"],
                idempotency_key=request["idempotency_key"],
                request_json=request_text,
                timestamp=timestamp,
            )
            state["pending_actions"][action_id] = pending_action_record(
                request, timestamp, authorization_verification
            )
            state = update_task(connection, row, state)
            append_event(
                connection,
                row["task_id"],
                "action-begun",
                {
                    "action_id": action_id,
                    "request": request,
                    "authorization_verification": authorization_verification,
                    "started_at": timestamp,
                    "state_version": state["state_version"],
                },
            )
            return {
                "action_id": action_id,
                "status": "pending",
                "state_version": state["state_version"],
                "reused": False,
                "state": state,
            }

        result = run_transaction(connection, "begin-action", begin)
        if "state" in result:
            refresh_snapshot_after_commit(store, result.pop("state"))
        return result
    finally:
        connection.close()


def command_resolve_action(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    receipt = validate_receipt(load_json(Path(args.receipt_file), dict))
    operations: list[object] = []
    if args.patch_file:
        operations = load_json(Path(args.patch_file), list)
    require_bounded_payload(operations, "action result patch")
    if receipt["status"] not in OUTCOME_RECEIPT_STATUSES[args.outcome]:
        raise StateError(
            f"{args.outcome} outcome requires receipt.status in "
            f"{sorted(OUTCOME_RECEIPT_STATUSES[args.outcome])}"
        )
    resolution = {
        "outcome": args.outcome,
        "receipt": receipt,
        "operations": operations,
    }
    require_bounded_payload(resolution, "action resolution")
    resolution_text = json_text(resolution)
    connection = connect(store)
    try:
        actions = ActionsRepository(connection)

        def resolve() -> dict[str, Any]:
            row = task_row(connection)
            action = actions.find_by_id(args.action_id)
            if not action:
                raise StateError(f"unknown action id: {args.action_id}")
            if receipt["idempotency_key"] != action["idempotency_key"]:
                raise StateError("receipt idempotency key does not match the action")
            if action["resolution_json"] == resolution_text:
                return state_from_row(row)
            if action["status"] != "pending":
                raise StateError(f"action is already resolved as {action['status']}")
            require_version(row, args.expected_version)
            state = state_from_row(row)
            require_active(state)
            state = apply_action_resolution(
                state,
                args.action_id,
                args.outcome,
                receipt,
                operations,
            )
            state = update_task(connection, row, state)
            next_status = "pending" if args.outcome == "pending" else args.outcome
            actions.resolve_pending(
                action_id=args.action_id,
                status=next_status,
                receipt_json=json_text(receipt),
                resolution_json=resolution_text,
                updated_at=now(),
            )
            event_kind = (
                "action-observed" if args.outcome == "pending" else "action-resolved"
            )
            append_event(
                connection,
                row["task_id"],
                event_kind,
                {
                    "action_id": args.action_id,
                    "outcome": args.outcome,
                    "receipt": receipt,
                    "operations": operations,
                    "state_version": state["state_version"],
                },
            )
            return state

        state = run_transaction(connection, "resolve-action", resolve)
        refresh_snapshot_after_commit(store, state)
        return state
    finally:
        connection.close()


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    return verify_store(Path(args.store).resolve())


def command_replay(args: argparse.Namespace) -> dict[str, Any]:
    return replay_store(Path(args.store).resolve())


def command_complete(args: argparse.Namespace) -> dict[str, Any]:
    store = Path(args.store).resolve()
    connection = connect(store)
    try:

        def complete() -> dict[str, Any]:
            row = task_row(connection)
            state = state_from_row(row)
            if state["task"]["status"] == "complete":
                return state
            require_version(row, args.expected_version)
            require_completion_ready(state)
            state["task"]["status"] = "complete"
            state = update_task(connection, row, state)
            append_event(
                connection,
                row["task_id"],
                "completed",
                {
                    "completion_evidence": state["completion_evidence"],
                    "state_version": state["state_version"],
                },
            )
            return state

        state = run_transaction(connection, "complete", complete)
        refresh_snapshot_after_commit(store, state)
        return state
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Maintain bounded, transactional execution state."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize a task state store")
    init.add_argument("--store", required=True)
    init.add_argument("--task-id", required=True)
    init.add_argument("--objective", required=True)
    init.add_argument("--criteria-file", required=True)
    init.add_argument("--constraints-file")
    init.add_argument("--max-state-bytes", type=int, default=DEFAULT_MAX_STATE_BYTES)
    init.set_defaults(handler=command_init)

    show = subparsers.add_parser("show", help="print the current state")
    show.add_argument("--store", required=True)
    show.set_defaults(handler=command_show)

    validate_patch = subparsers.add_parser(
        "validate-patch", help="validate a local patch without committing it"
    )
    validate_patch.add_argument("--store", required=True)
    validate_patch.add_argument("--expected-version", required=True, type=int)
    validate_patch.add_argument("--patch-file", required=True)
    validate_patch.set_defaults(handler=command_validate_patch)

    apply_patch = subparsers.add_parser(
        "apply-patch", help="apply a validated local state patch"
    )
    apply_patch.add_argument("--store", required=True)
    apply_patch.add_argument("--expected-version", required=True, type=int)
    apply_patch.add_argument("--patch-file", required=True)
    apply_patch.set_defaults(handler=command_apply_patch)

    begin_action = subparsers.add_parser(
        "begin-action", help="record a pending external action"
    )
    begin_action.add_argument("--store", required=True)
    begin_action.add_argument("--expected-version", required=True, type=int)
    begin_action.add_argument("--action-file", required=True)
    authorization = begin_action.add_mutually_exclusive_group()
    authorization.add_argument(
        "--authorization-verifier",
        help=(
            "caller-supplied verifier path; path checks do not establish host trust, "
            "so production hosts must pin this argument outside model control"
        ),
    )
    authorization.add_argument(
        "--allow-reference-authorization",
        action="store_true",
        help=(
            "record an unverified reference for a non-executing rehearsal/test; "
            "this never authorizes external tool execution"
        ),
    )
    begin_action.set_defaults(handler=command_begin_action)

    resolve_action = subparsers.add_parser(
        "resolve-action", help="reconcile a pending action from its receipt"
    )
    resolve_action.add_argument("--store", required=True)
    resolve_action.add_argument("--expected-version", required=True, type=int)
    resolve_action.add_argument("--action-id", required=True)
    resolve_action.add_argument(
        "--outcome", choices=tuple(sorted(ACTION_OUTCOMES)), required=True
    )
    resolve_action.add_argument("--receipt-file", required=True)
    resolve_action.add_argument("--patch-file")
    resolve_action.set_defaults(handler=command_resolve_action)

    verify = subparsers.add_parser("verify", help="verify internal store invariants")
    verify.add_argument("--store", required=True)
    verify.set_defaults(handler=command_verify)

    replay = subparsers.add_parser(
        "replay", help="replay the event ledger and compare current state"
    )
    replay.add_argument("--store", required=True)
    replay.set_defaults(handler=command_replay)

    complete = subparsers.add_parser(
        "complete", help="mark a fully evidenced task complete"
    )
    complete.add_argument("--store", required=True)
    complete.add_argument("--expected-version", required=True, type=int)
    complete.set_defaults(handler=command_complete)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "max_state_bytes", 1) <= 0:
        parser.error("--max-state-bytes must be positive")
    try:
        result = args.handler(args)
    except (OSError, sqlite3.Error, StateError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0
