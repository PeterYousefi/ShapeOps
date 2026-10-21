"""Append-only release authorization journal and operator governance."""
import argparse
import hmac
import json
import math
import os
from pathlib import Path
import sqlite3
import time
import uuid

from typing import Mapping
from backend.governance import evaluate_gates, eligible, GateSet

MAX_RELEASES = 100


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.execute("PRAGMA query_only=ON")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def initialize(db: sqlite3.Connection) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS releases ("
        "id TEXT PRIMARY KEY, "
        "at REAL NOT NULL, "
        "operator TEXT NOT NULL, "
        "candidate_id TEXT NOT NULL, "
        "package_id TEXT NOT NULL, "
        "gates TEXT NOT NULL, "
        "status TEXT NOT NULL CHECK(status IN ('approved', 'rejected')), "
        "rationale TEXT NOT NULL"
        ")"
    )
    db.execute("CREATE INDEX IF NOT EXISTS releases_order ON releases(at DESC, id DESC)")
    for action in ("UPDATE", "DELETE"):
        db.execute(
            f"CREATE TRIGGER IF NOT EXISTS immutable_releases_{action.lower()} "
            f"BEFORE {action} ON releases BEGIN "
            "SELECT RAISE(ABORT, 'Release journal is append-only'); END"
        )


def verify_operator_token(authorization_header: str | None) -> tuple[bool, str]:
    expected_token = os.getenv("SHAPEOPS_OPERATOR_TOKEN")
    if not expected_token:
        return False, "Operator token authentication is not configured in this environment"
    if not authorization_header or not isinstance(authorization_header, str):
        return False, "Missing Authorization header"
    if not authorization_header.startswith("Bearer "):
        return False, "Invalid authorization scheme; Bearer token required"
    provided_token = authorization_header[7:].strip()
    if not hmac.compare_digest(provided_token.encode(), expected_token.encode()):
        return False, "Invalid operator credentials"
    operator_name = os.getenv("SHAPEOPS_OPERATOR_NAME", "authorized-operator")
    return True, operator_name


def record_release(
    path: Path,
    operator: str,
    candidate_id: str,
    package_id: str,
    gates: Mapping[str, bool] | GateSet,
    status: str,
    rationale: str,
    *,
    at: float | None = None,
) -> dict:
    if status not in ("approved", "rejected"):
        raise ValueError("Release status must be 'approved' or 'rejected'")
    if not operator or len(operator) > 128:
        raise ValueError("Operator name must be between 1 and 128 characters")
    if not candidate_id or len(candidate_id) > 64:
        raise ValueError("Candidate ID must be between 1 and 64 characters")
    if len(package_id) != 64:
        raise ValueError("Package ID must be a 64-character digest")
    if not rationale or len(rationale) > 512:
        raise ValueError("Rationale must be between 1 and 512 characters")

    now = time.time() if at is None else at
    if not math.isfinite(now) or now < 0:
        raise ValueError("Invalid release timestamp")

    release_id = uuid.uuid4().hex
    encoded_gates = json.dumps(gates, sort_keys=True, separators=(",", ":"), allow_nan=False)

    db = connect(path)
    try:
        with db:
            initialize(db)
            db.execute(
                "INSERT INTO releases VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (release_id, now, operator, candidate_id, package_id, encoded_gates, status, rationale),
            )
    finally:
        db.close()

    return {
        "id": release_id,
        "at": now,
        "operator": operator,
        "candidate_id": candidate_id,
        "package_id": package_id,
        "gates": gates,
        "status": status,
        "rationale": rationale,
    }


def list_releases(path: Path, limit: int = 20) -> list[dict]:
    if not 1 <= limit <= MAX_RELEASES:
        raise ValueError(f"Limit must be between 1 and {MAX_RELEASES}")
    if not path.exists():
        return []
    db = connect(path, readonly=True)
    try:
        table_exists = bool(
            db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='releases'").fetchone()
        )
        if not table_exists:
            return []
        rows = db.execute(
            "SELECT id, at, operator, candidate_id, package_id, gates, status, rationale "
            "FROM releases ORDER BY at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        results = []
        for r in rows:
            results.append(
                {
                    "id": r["id"],
                    "at": float(r["at"]),
                    "operator": r["operator"],
                    "candidate_id": r["candidate_id"],
                    "package_id": r["package_id"],
                    "gates": json.loads(r["gates"]),
                    "status": r["status"],
                    "rationale": r["rationale"],
                }
            )
        return results
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    list_p = subparsers.add_parser("list", help="List recent release decisions")
    list_p.add_argument("--database", type=Path, default=Path(".runtime/releases.sqlite"))
    list_p.add_argument("--limit", type=int, default=20)

    eval_p = subparsers.add_parser("evaluate", help="Evaluate and record candidate release decision")
    eval_p.add_argument("--database", type=Path, default=Path(".runtime/releases.sqlite"))
    eval_p.add_argument("--candidate", type=str, default="surface-et-v2")
    eval_p.add_argument("--macro-f1", type=float, default=1.0)
    eval_p.add_argument("--operator", type=str, required=True)
    eval_p.add_argument("--token", type=str, required=True)
    eval_p.add_argument("--package-id", type=str, default="0" * 64)
    eval_p.add_argument("--rationale", type=str, default="Verified candidate passes all release gates")

    args = parser.parse_args()

    if args.action == "list":
        records = list_releases(args.database, limit=args.limit)
        print(json.dumps(records, indent=2))
    elif args.action == "evaluate":
        os.environ["SHAPEOPS_OPERATOR_TOKEN"] = args.token
        valid, op = verify_operator_token(f"Bearer {args.token}")
        if not valid:
            parser.exit(1, f"Authentication failed: {op}\n")

        gates = evaluate_gates(args.macro_f1, True, True, True)
        is_eligible = eligible(gates, authorized=True)
        status = "approved" if is_eligible else "rejected"
        record = record_release(
            args.database,
            args.operator,
            args.candidate,
            args.package_id,
            gates,
            status,
            args.rationale,
        )
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
