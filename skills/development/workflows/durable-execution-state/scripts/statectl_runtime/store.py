from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any, Callable, TypeVar

from .errors import StateError
from .faults import inject_fault
from .model import json_text, now, require_bounded_payload, validate_state


DATABASE_NAME = "state.db"
SNAPSHOT_NAME = "state.snapshot.json"
T = TypeVar("T")


class ActionsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def find_by_idempotency_key(self, idempotency_key: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM actions WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()

    def find_by_id(self, action_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM actions WHERE action_id = ?",
            (action_id,),
        ).fetchone()

    def iter_all(self) -> Iterator[sqlite3.Row]:
        yield from self.connection.execute(
            "SELECT action_id, task_id, idempotency_key, status, request_json, "
            "receipt_json, resolution_json FROM actions ORDER BY action_id"
        )

    def insert_pending(
        self,
        *,
        action_id: str,
        task_id: str,
        idempotency_key: str,
        request_json: str,
        timestamp: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO actions(
                action_id, task_id, idempotency_key, status, request_json,
                receipt_json, resolution_json, created_at, updated_at
            ) VALUES (?, ?, ?, 'pending', ?, NULL, NULL, ?, ?)
            """,
            (
                action_id,
                task_id,
                idempotency_key,
                request_json,
                timestamp,
                timestamp,
            ),
        )

    def resolve_pending(
        self,
        *,
        action_id: str,
        status: str,
        receipt_json: str,
        resolution_json: str,
        updated_at: str,
    ) -> None:
        updated = self.connection.execute(
            """
            UPDATE actions
            SET status = ?, receipt_json = ?, resolution_json = ?, updated_at = ?
            WHERE action_id = ? AND status = 'pending'
            """,
            (
                status,
                receipt_json,
                resolution_json,
                updated_at,
                action_id,
            ),
        )
        if updated.rowcount != 1:
            raise StateError("action status changed during transaction")


def connect(store: Path, *, create: bool = False) -> sqlite3.Connection:
    database = store / DATABASE_NAME
    if not create and not database.is_file():
        raise StateError(f"state store does not exist: {store}")
    if create:
        store.mkdir(parents=True, exist_ok=True)
    store.chmod(0o700)
    connection = sqlite3.connect(database, isolation_level=None)
    database.chmod(0o600)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def create_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            state_version INTEGER NOT NULL,
            status TEXT NOT NULL,
            state_json TEXT NOT NULL,
            max_state_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL REFERENCES tasks(task_id),
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS actions (
            action_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL REFERENCES tasks(task_id),
            idempotency_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            request_json TEXT NOT NULL,
            receipt_json TEXT,
            resolution_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )


def task_row(connection: sqlite3.Connection) -> sqlite3.Row:
    rows = connection.execute("SELECT * FROM tasks ORDER BY created_at").fetchall()
    if len(rows) != 1:
        raise StateError(f"expected exactly one task in store, found {len(rows)}")
    return rows[0]


def state_from_row(row: sqlite3.Row) -> dict[str, Any]:
    state = json.loads(row["state_json"])
    if not isinstance(state, dict):
        raise StateError("stored state is not a JSON object")
    return state


def write_snapshot(store: Path, state: dict[str, Any]) -> None:
    store.mkdir(parents=True, exist_ok=True)
    data = json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".state.snapshot.",
        suffix=".tmp",
        dir=store,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        snapshot = store / SNAPSHOT_NAME
        os.replace(temporary, snapshot)
        snapshot.chmod(0o400)
    finally:
        temporary.unlink(missing_ok=True)


def refresh_snapshot_after_commit(store: Path, state: dict[str, Any]) -> None:
    try:
        write_snapshot(store, state)
    except OSError as error:
        print(
            "WARNING: SQLite state committed but snapshot refresh failed; "
            f"run show or verify to regenerate it: {error}",
            file=sys.stderr,
        )


def append_event(
    connection: sqlite3.Connection,
    task_id: str,
    kind: str,
    payload: object,
) -> None:
    require_bounded_payload(payload, f"{kind} event")
    connection.execute(
        "INSERT INTO events(task_id, kind, payload_json, created_at) VALUES (?, ?, ?, ?)",
        (task_id, kind, json_text(payload), now()),
    )


def update_task(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    state: dict[str, Any],
) -> dict[str, Any]:
    next_version = row["state_version"] + 1
    state["state_version"] = next_version
    validate_state(state, row["max_state_bytes"])
    result = connection.execute(
        """
        UPDATE tasks
        SET state_version = ?, status = ?, state_json = ?, updated_at = ?
        WHERE task_id = ? AND state_version = ?
        """,
        (
            next_version,
            state["task"]["status"],
            json_text(state),
            now(),
            row["task_id"],
            row["state_version"],
        ),
    )
    if result.rowcount != 1:
        raise StateError("state version changed during transaction")
    return state


def require_version(row: sqlite3.Row, expected_version: int) -> None:
    if row["state_version"] != expected_version:
        raise StateError(
            f"stale state version: expected {expected_version}, "
            f"current {row['state_version']}"
        )


def run_transaction(
    connection: sqlite3.Connection,
    operation_name: str,
    operation: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    connection.execute("BEGIN IMMEDIATE")
    try:
        result = operation()
        inject_fault(f"{operation_name}.before-commit")
        connection.execute("COMMIT")
        inject_fault(f"{operation_name}.after-commit")
        return result
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


def run_read_transaction(
    connection: sqlite3.Connection,
    operation: Callable[[], T],
) -> T:
    connection.execute("PRAGMA query_only = ON")
    connection.execute("BEGIN")
    try:
        result = operation()
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    if connection.in_transaction:
        connection.execute("ROLLBACK")
    return result
