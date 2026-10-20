"""Local append-only completed training journal; no release authority is granted."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialize(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS training_runs (id TEXT PRIMARY KEY, started_at REAL NOT NULL, completed_at REAL NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS run_models (run_id TEXT NOT NULL REFERENCES training_runs(id), model_id TEXT NOT NULL, package_id TEXT NOT NULL, manifest TEXT NOT NULL, PRIMARY KEY(run_id,model_id))")
    db.execute("CREATE INDEX IF NOT EXISTS training_runs_order ON training_runs(completed_at DESC,id DESC)")
    for table in ("training_runs", "run_models"):
        for action in ("UPDATE", "DELETE"):
            db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'Training journal is append-only'); END")


def record_run(path: Path, started_at: float, records: list[dict]) -> str:
    if not records or len(records) > 16:
        raise ValueError("A training run requires one to sixteen completed model packages")
    snapshots = []
    for record in records:
        manifest = {key: value for key, value in record.items() if key != "package_id"}
        encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if hashlib.sha256(encoded.encode()).hexdigest() != record.get("package_id"):
            raise ValueError("Training run package identity does not match its manifest")
        snapshots.append((record["id"], record["package_id"], encoded))
    run_id = uuid.uuid4().hex
    completed_at = time.time()
    if not 0 <= started_at <= completed_at:
        raise ValueError("Invalid training run timestamps")
    db = connect(path)
    try:
        with db:
            initialize(db)
            db.execute("INSERT INTO training_runs VALUES (?,?,?)", (run_id, started_at, completed_at))
            db.executemany("INSERT INTO run_models VALUES (?,?,?,?)", [(run_id, *snapshot) for snapshot in snapshots])
    finally:
        db.close()
    return run_id


def list_runs(path: Path, limit: int = 20) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("History limit must be between one and one hundred")
    if not path.exists():
        return []
    db = connect(path)
    try:
        rows = db.execute("SELECT * FROM training_runs ORDER BY completed_at DESC,id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(row), "models": [dict(model) for model in db.execute(
            "SELECT model_id,package_id FROM run_models WHERE run_id=? ORDER BY model_id", (row["id"],)
        )]} for row in rows]
    finally:
        db.close()


def get_run(path: Path, run_id: str) -> dict | None:
    if not path.exists():
        return None
    db = connect(path)
    try:
        row = db.execute("SELECT * FROM training_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            return None
        models = []
        for model in db.execute("SELECT * FROM run_models WHERE run_id=? ORDER BY model_id", (run_id,)):
            encoded = model["manifest"]
            if hashlib.sha256(encoded.encode()).hexdigest() != model["package_id"]:
                raise ValueError("Training journal manifest integrity check failed")
            models.append({**json.loads(encoded), "package_id": model["package_id"]})
        return {**dict(row), "models": models}
    finally:
        db.close()
