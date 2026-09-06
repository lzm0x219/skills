#!/usr/bin/env python3
"""Example verifier: a host-pinned approval file must bind the exact request.

This program does not establish host trust or grant permission. The host must
protect the program, interpreter, wrapper and approval file from model writes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import sys


def same_text(left: object, right: object) -> bool:
    return (
        isinstance(left, str) and isinstance(right, str)
        and hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
    )


def bounded_object(raw: bytes, limit: int) -> dict:
    if len(raw) > limit:
        raise ValueError("JSON payload exceeds limit")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object")
    return value


def verify(payload: dict, approval: dict) -> dict:
    if set(payload) != {"request", "request_sha256"} or not isinstance(payload["request"], dict):
        raise ValueError("invalid request envelope")
    required = {"authorized", "authorization_ref", "request_sha256", "verifier_ref", "expires_at"}
    if set(approval) != required or approval["authorized"] is not True:
        raise ValueError("no matching host approval")
    request = payload["request"]
    digest = hashlib.sha256(json.dumps(
        request, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    if not same_text(digest, payload["request_sha256"]) or not same_text(digest, approval["request_sha256"]):
        raise ValueError("request hash does not match host approval")
    reference = request.get("authorization_ref")
    if not isinstance(reference, str) or not reference.strip() or not same_text(reference, approval["authorization_ref"]):
        raise ValueError("authorization reference does not match host approval")
    if not isinstance(approval["verifier_ref"], str) or not approval["verifier_ref"].strip():
        raise ValueError("verifier_ref must be non-empty")
    expiry = approval["expires_at"]
    if not isinstance(expiry, str):
        raise ValueError("expires_at must be UTC YYYY-MM-DDTHH:MM:SSZ")
    expires_at = datetime.strptime(expiry, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if expires_at.strftime("%Y-%m-%dT%H:%M:%SZ") != expiry:
        raise ValueError("expires_at must use zero-padded UTC fields")
    now = datetime.now(timezone.utc)
    if expires_at <= now:
        raise ValueError("host approval has expired")
    return {
        "authorized": True, "authorization_ref": reference, "request_sha256": digest,
        "verifier_ref": approval["verifier_ref"], "verified_at": now.isoformat(),
        "expires_at": expiry,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-file", type=Path, required=True,
                        help="host-pinned file; never select it from model input")
    args = parser.parse_args()
    try:
        payload = bounded_object(sys.stdin.buffer.read(131073), 131072)
        with args.approval_file.open("rb") as stream:
            approval = bounded_object(stream.read(65537), 65536)
        response = verify(payload, approval)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        print("DENIED: invalid, expired or mismatched host approval", file=sys.stderr)
        return 1
    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
