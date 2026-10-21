"""Local append-only completed training journal; no release authority is granted."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
import uuid


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        # URI escaping preserves spaces, question marks and hashes in local paths.
        # mode=ro also fails closed if the file disappears after an existence check.
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.execute("PRAGMA query_only=ON")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialize(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS training_runs (id TEXT PRIMARY KEY, started_at REAL NOT NULL, completed_at REAL NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS run_models (run_id TEXT NOT NULL REFERENCES training_runs(id), model_id TEXT NOT NULL, package_id TEXT NOT NULL, manifest TEXT NOT NULL, PRIMARY KEY(run_id,model_id))")
    db.execute("CREATE INDEX IF NOT EXISTS training_runs_order ON training_runs(completed_at DESC,id DESC)")
    db.execute("CREATE TABLE IF NOT EXISTS training_failures (id TEXT PRIMARY KEY, started_at REAL NOT NULL, failed_at REAL NOT NULL CHECK(failed_at >= started_at), category TEXT NOT NULL CHECK(category IN ('validation','storage','execution')))")
    db.execute("CREATE INDEX IF NOT EXISTS training_failures_order ON training_failures(failed_at DESC,id DESC)")
    for table in ("training_runs", "run_models", "training_failures"):
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


def _read_models(db: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = db.execute(
        "SELECT model_id,package_id,manifest FROM run_models WHERE run_id=? ORDER BY model_id LIMIT 17",
        (run_id,),
    ).fetchall()
    if not 1 <= len(rows) <= 16:
        raise ValueError("Training journal model count integrity check failed")
    models = []
    for row in rows:
        encoded = row["manifest"]
        if hashlib.sha256(encoded.encode()).hexdigest() != row["package_id"]:
            raise ValueError("Training journal manifest integrity check failed")
        try:
            manifest = json.loads(encoded)
        except json.JSONDecodeError:
            raise ValueError("Training journal manifest integrity check failed") from None
        if not isinstance(manifest, dict) or manifest.get("id") != row["model_id"] or "package_id" in manifest:
            raise ValueError("Training journal model identity integrity check failed")
        models.append({**manifest, "package_id": row["package_id"]})
    return models


def list_runs(path: Path, limit: int = 20) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("History limit must be between one and one hundred")
    if not path.exists():
        return []
    db = connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        rows = db.execute("SELECT * FROM training_runs ORDER BY completed_at DESC,id DESC LIMIT ?", (limit,)).fetchall()
        runs = []
        for row in rows:
            models = _read_models(db, row["id"])
            references = [{"model_id": model["id"], "package_id": model["package_id"]} for model in models]
            runs.append({**dict(row), "models": references})
        return runs
    finally:
        db.close()


def get_run(path: Path, run_id: str) -> dict | None:
    if not path.exists():
        return None
    db = connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        row = db.execute("SELECT * FROM training_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            return None
        models = _read_models(db, run_id)
        return {**dict(row), "models": models}
    finally:
        db.close()


def record_failure(path: Path, started_at: float, category: str) -> str:
    failed_at = time.time()
    if (not math.isfinite(started_at) or not 0 <= started_at <= failed_at
            or category not in {"validation", "storage", "execution"}):
        raise ValueError("Invalid failed training attempt metadata")
    identity = uuid.uuid4().hex
    db = connect(path)
    try:
        with db:
            initialize(db)
            db.execute("INSERT INTO training_failures VALUES (?,?,?,?)", (identity, started_at, failed_at, category))
    finally:
        db.close()
    return identity


def list_failures(path: Path, limit: int = 20) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("History limit must be between one and one hundred")
    if not path.exists():
        return []
    db = connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        # Existing journals predate failure capture; reads never migrate them.
        if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='training_failures'").fetchone() is None:
            return []
        return [dict(row) for row in db.execute(
            "SELECT id,started_at,failed_at,category FROM training_failures ORDER BY failed_at DESC,id DESC LIMIT ?",
            (limit,),
        )]
    finally:
        db.close()
