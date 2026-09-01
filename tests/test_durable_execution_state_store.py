#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
STATECTL = (
    ROOT
    / "skills"
    / "development"
    / "workflows"
    / "durable-execution-state"
    / "scripts"
    / "statectl.py"
)
RUNTIME_ROOT = STATECTL.parent
sys.path.insert(0, str(RUNTIME_ROOT))

from statectl_runtime import replay as replay_runtime  # noqa: E402
from statectl_runtime import store as store_runtime  # noqa: E402
from statectl_runtime.errors import StateError  # noqa: E402


class NoFetchAllCursor:
    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self.cursor = cursor

    def __iter__(self) -> NoFetchAllCursor:
        return self

    def __next__(self) -> sqlite3.Row:
        row = self.cursor.fetchone()
        if row is None:
            raise StopIteration
        return row

    def fetchall(self) -> list[sqlite3.Row]:
        raise AssertionError("event replay must not materialize the full event log")


class StreamingEventConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def execute(
        self, statement: str, parameters: tuple[object, ...] = ()
    ) -> sqlite3.Cursor | NoFetchAllCursor:
        cursor = self.connection.execute(statement, parameters)
        if " FROM events " in f" {statement} ":
            return NoFetchAllCursor(cursor)
        return cursor


class DurableExecutionStateStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="durable-execution-state-store-test-"
        )
        self.root = Path(self.temporary.name)
        self.store = self.root / "store"
        self.criteria = self.root / "criteria.json"
        self.criteria.write_text(
            json.dumps([{"id": "done", "description": "Task is done"}]) + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_init_hardens_store_database_and_snapshot_permissions(self) -> None:
        self.run_statectl(
            "init",
            "--store",
            str(self.store),
            "--task-id",
            "release-1",
            "--objective",
            "Ship safely",
            "--criteria-file",
            str(self.criteria),
        )

        self.assertEqual(0o700, stat.S_IMODE(self.store.stat().st_mode))
        self.assertEqual(
            0o600,
            stat.S_IMODE((self.store / "state.db").stat().st_mode),
        )
        self.assertEqual(
            0o400,
            stat.S_IMODE((self.store / "state.snapshot.json").stat().st_mode),
        )

    def test_verify_repairs_snapshot_after_one_explicit_read_transaction(self) -> None:
        self.init_store()
        snapshot = self.store / "state.snapshot.json"
        snapshot.unlink()
        connection = sqlite3.connect(
            self.store / "state.db",
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        statements: list[str] = []
        connection.set_trace_callback(statements.append)
        snapshot_transaction_states: list[bool] = []
        original_write_snapshot = replay_runtime.write_snapshot

        def observe_snapshot_write(
            store: Path, state: dict[str, object]
        ) -> None:
            snapshot_transaction_states.append(connection.in_transaction)
            original_write_snapshot(store, state)

        with (
            patch.object(replay_runtime, "connect", return_value=connection),
            patch.object(
                replay_runtime,
                "write_snapshot",
                side_effect=observe_snapshot_write,
            ),
        ):
            verified = replay_runtime.verify_store(self.store)

        self.assertTrue(verified["verified"])
        transaction_statements = [
            statement.strip().upper()
            for statement in statements
            if statement.strip().upper() in {"BEGIN", "ROLLBACK", "COMMIT"}
        ]
        self.assertEqual(["BEGIN", "ROLLBACK"], transaction_statements)
        self.assertEqual([False], snapshot_transaction_states)
        self.assertTrue(snapshot.is_file())

    def test_verify_rolls_back_read_transaction_on_base_exception(self) -> None:
        self.init_store()
        connection = sqlite3.connect(
            self.store / "state.db",
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        statements: list[str] = []
        connection.set_trace_callback(statements.append)

        with (
            patch.object(replay_runtime, "connect", return_value=connection),
            patch.object(
                replay_runtime,
                "replay_events",
                side_effect=KeyboardInterrupt("interrupted verification"),
            ),
            self.assertRaisesRegex(KeyboardInterrupt, "interrupted verification"),
        ):
            replay_runtime.verify_store(self.store)

        transaction_statements = [
            statement.strip().upper()
            for statement in statements
            if statement.strip().upper() in {"BEGIN", "ROLLBACK", "COMMIT"}
        ]
        self.assertEqual(["BEGIN", "ROLLBACK"], transaction_statements)

    def test_replay_streams_events_and_reports_the_exact_count(self) -> None:
        expected_state = self.init_store()
        connection = store_runtime.connect(self.store)
        try:
            row = store_runtime.task_row(connection)
            replayed, actions, event_count, state_digest = (
                replay_runtime.replay_events(StreamingEventConnection(connection), row)
            )
        finally:
            connection.close()

        self.assertEqual(expected_state, replayed)
        self.assertEqual({}, actions)
        self.assertEqual(1, event_count)
        self.assertEqual(64, len(state_digest))

    def test_actions_repository_inserts_and_finds_pending_actions(self) -> None:
        self.init_store()
        connection = store_runtime.connect(self.store)
        try:
            repository = store_runtime.ActionsRepository(connection)
            repository.insert_pending(
                action_id="action-1",
                task_id="release-1",
                idempotency_key="publish:release-1",
                request_json='{"tool":"publish"}',
                timestamp="2026-09-01T00:00:00Z",
            )

            by_key = repository.find_by_idempotency_key("publish:release-1")
            by_id = repository.find_by_id("action-1")
            all_actions = list(repository.iter_all())
        finally:
            connection.close()

        self.assertIsNotNone(by_key)
        self.assertIsNotNone(by_id)
        assert by_key is not None
        assert by_id is not None
        self.assertEqual("action-1", by_key["action_id"])
        self.assertEqual("pending", by_id["status"])
        self.assertEqual(["action-1"], [row["action_id"] for row in all_actions])

    def test_actions_repository_resolves_only_pending_action(self) -> None:
        self.init_store()
        connection = store_runtime.connect(self.store)
        try:
            repository = store_runtime.ActionsRepository(connection)
            repository.insert_pending(
                action_id="action-1",
                task_id="release-1",
                idempotency_key="publish:release-1",
                request_json='{"tool":"publish"}',
                timestamp="2026-09-01T00:00:00Z",
            )

            repository.resolve_pending(
                action_id="action-1",
                status="confirmed",
                receipt_json='{"status":"succeeded"}',
                resolution_json='{"outcome":"confirmed"}',
                updated_at="2026-09-01T00:01:00Z",
            )
            resolved = repository.find_by_id("action-1")
            with self.assertRaisesRegex(
                StateError, "action status changed during transaction"
            ):
                repository.resolve_pending(
                    action_id="action-1",
                    status="failed",
                    receipt_json='{"status":"failed"}',
                    resolution_json='{"outcome":"failed"}',
                    updated_at="2026-09-01T00:02:00Z",
                )
        finally:
            connection.close()

        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual("confirmed", resolved["status"])
        self.assertEqual('{"status":"succeeded"}', resolved["receipt_json"])
        self.assertEqual(
            '{"outcome":"confirmed"}', resolved["resolution_json"]
        )
        self.assertEqual("2026-09-01T00:01:00Z", resolved["updated_at"])

    def run_statectl(self, *arguments: str) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, str(STATECTL), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIsInstance(result, dict)
        return result

    def init_store(self) -> dict[str, object]:
        return self.run_statectl(
            "init",
            "--store",
            str(self.store),
            "--task-id",
            "release-1",
            "--objective",
            "Ship safely",
            "--criteria-file",
            str(self.criteria),
        )


if __name__ == "__main__":
    unittest.main()
