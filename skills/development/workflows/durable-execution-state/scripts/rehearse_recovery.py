#!/usr/bin/env python3
"""Exercise recovery in disposable local stores; never dispatch a real external tool."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time


STATECTL = Path(__file__).with_name("statectl.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_json(root: Path, name: str, value: object) -> Path:
    path = root / name
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def run_cli(*args: object, fault: str | None = None) -> dict:
    environment = os.environ.copy()
    environment.pop("STATECTL_FAULT_POINT", None)
    if fault:
        environment["STATECTL_FAULT_POINT"] = fault
    result = subprocess.run(
        [sys.executable, str(STATECTL), *(str(arg) for arg in args)],
        env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if fault:
        require(
            result.returncode == 2 and f"fault injected at {fault}" in result.stderr,
            f"expected injected fault, got: {result.stderr}",
        )
        return {}
    require(result.returncode == 0, result.stderr)
    return json.loads(result.stdout)


def rehearse(steps: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="statectl-rehearsal-") as directory:
        root = Path(directory)
        store = root / "state"
        criteria = write_json(root, "criteria.json", [{
            "id": "recovered", "description": "Local simulated receipt recovered"
        }])
        run_cli("init", "--store", store, "--task-id", "rehearsal",
                "--objective", "Rehearse local recovery only", "--criteria-file", criteria)
        patch_times = []
        peak_state_bytes = 0
        for version in range(steps):
            patch = write_json(root, "patch.json", [{
                "op": "add" if version == 0 else "replace",
                "path": "/plan/current", "value": {"step": version + 1},
            }])
            started = time.perf_counter()
            state = run_cli("apply-patch", "--store", store, "--expected-version", version,
                            "--patch-file", patch)
            patch_times.append((time.perf_counter() - started) * 1000)
            state_bytes = len(json.dumps(
                state, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"))
            peak_state_bytes = max(peak_state_bytes, state_bytes)

        # A precommit failure leaves the previous version intact.
        patch = write_json(root, "patch.json", [{
            "op": "replace", "path": "/plan/current", "value": {"step": "not committed"}
        }])
        run_cli("apply-patch", "--store", store, "--expected-version", steps,
                "--patch-file", patch, fault="apply-patch.before-commit")
        state = run_cli("show", "--store", store)
        require(state["state_version"] == steps, "precommit fault changed version")
        require(state["plan"]["current"] == {"step": steps}, "rollback lost the old value")

        # The action is only a local simulation: no publisher, network or host verifier.
        key = "rehearsal:effect-1"
        action = write_json(root, "action.json", {
            "idempotency_key": key, "tool": "local-simulation", "args": {},
            "authorization_ref": "rehearsal://non-executing",
            "preconditions": [{"path": "/plan/current/step", "operator": "equals", "value": steps}],
        })
        begin_args = ("begin-action", "--store", store, "--expected-version", steps,
                      "--action-file", action, "--allow-reference-authorization")
        run_cli(*begin_args, fault="begin-action.after-commit")
        (store / "state.snapshot.json").unlink(missing_ok=True)
        state = run_cli("show", "--store", store)
        require(state["state_version"] == steps + 1, "postcommit action disappeared")
        require(len(state["pending_actions"]) == 1, "pending action was not recovered")
        require(run_cli("verify", "--store", store)["verified"], "recovery verification failed")
        begun = run_cli(*begin_args)
        require(begun["reused"] and begun["state_version"] == steps + 1, "duplicate registration")

        # A fake service ledger is authoritative only for this disposable rehearsal.
        ledger = write_json(root, "simulated-service.json", {key: {"object_id": "fake-1"}})
        observed = json.loads(ledger.read_text(encoding="utf-8"))
        require(list(observed) == [key], "unexpected simulated effect")
        timestamp = datetime.now(timezone.utc).isoformat()
        receipt = write_json(root, "receipt.json", {
            "status": "succeeded", "idempotency_key": key,
            "source_ref": ledger.as_uri(), "observed_at": timestamp,
            "details": {"rehearsal": True, **observed[key]},
        })
        resolve_args = ("resolve-action", "--store", store, "--expected-version", steps + 1,
                        "--action-id", begun["action_id"], "--outcome", "confirmed",
                        "--receipt-file", receipt)
        run_cli(*resolve_args, fault="resolve-action.after-commit")
        state = run_cli("show", "--store", store)
        require(not state["pending_actions"], "committed receipt was not recovered")
        retried = run_cli(*resolve_args)
        require(retried["state_version"] == steps + 2, "receipt retry changed state")

        evidence = write_json(root, "evidence.json", [{
            "op": "add", "path": "/completion_evidence/recovered",
            "value": {"source_ref": ledger.as_uri(), "observed_at": timestamp},
        }])
        run_cli("apply-patch", "--store", store, "--expected-version", steps + 2,
                "--patch-file", evidence)
        state = run_cli("complete", "--store", store, "--expected-version", steps + 3)
        started = time.perf_counter()
        replay = run_cli("replay", "--store", store)
        replay_ms = (time.perf_counter() - started) * 1000
        verified = run_cli("verify", "--store", store)
        require(state["task"]["status"] == "complete", "task did not complete")
        require(replay["event_count"] == steps + 5, "retries added unexpected events")
        require(verified["verified"], "final verification failed")
        return {
            "scope": "disposable-local-protocol-rehearsal", "real_external_actions": 0,
            "host_trust_verified": False, "steps": steps,
            "final_state_version": state["state_version"], "event_count": replay["event_count"],
            "verified": verified["verified"], "task_status": state["task"]["status"],
            "checks": ["precommit-rollback", "postcommit-action-recovery", "snapshot-rebuild",
                       "registration-reuse", "postcommit-receipt-recovery", "receipt-reuse"],
            "peak_patch_state_bytes": peak_state_bytes,
            "final_state_bytes": replay["state_size_bytes"],
            "cli_patch_median_ms": round(statistics.median(patch_times), 3),
            "cli_patch_p95_ms": round(sorted(patch_times)[math.ceil(0.95 * steps) - 1], 3),
            "cli_replay_ms": round(replay_ms, 3),
            "measurement_scope": "CLI wall time includes interpreter startup; not model tokens or process RAM",
            "python": platform.python_version(), "platform": platform.platform(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100, help="local transitions, 1 to 10000")
    args = parser.parse_args()
    if not 1 <= args.steps <= 10000:
        parser.error("--steps must be between 1 and 10000")
    try:
        result = rehearse(args.steps)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
