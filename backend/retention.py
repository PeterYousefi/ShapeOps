"""Bound local operational records; callers own the SQLite transaction."""
import sqlite3
import time

REQUEST_MAX_ROWS = 1000
REQUEST_MAX_AGE_SECONDS = 7 * 86400
DRILL_MAX_ROWS = 200
DRILL_MAX_AGE_SECONDS = 30 * 86400


def prune_records(db: sqlite3.Connection, *, now: float | None = None) -> None:
    cutoff_time = time.time() if now is None else now
    # Table names are fixed program constants, never request-controlled SQL.
    for table, age, limit in (
        ("requests", REQUEST_MAX_AGE_SECONDS, REQUEST_MAX_ROWS),
        ("drills", DRILL_MAX_AGE_SECONDS, DRILL_MAX_ROWS),
    ):
        db.execute(f"DELETE FROM {table} WHERE at < ?", (cutoff_time - age,))
        db.execute(
            f"DELETE FROM {table} WHERE id IN "
            f"(SELECT id FROM {table} ORDER BY at DESC, id DESC LIMIT -1 OFFSET ?)",
            (limit,),
        )

    if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drift_observations'").fetchone():
        db.execute("DELETE FROM drift_observations WHERE NOT EXISTS (SELECT 1 FROM requests WHERE requests.id=drift_observations.id)")


def initialize_retention(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS drift_observations (id TEXT PRIMARY KEY, at REAL NOT NULL, result TEXT NOT NULL)")
    db.execute("CREATE INDEX IF NOT EXISTS drift_retention ON drift_observations(at DESC,id DESC)")
    db.execute("CREATE INDEX IF NOT EXISTS requests_retention ON requests(at DESC, id DESC)")
    db.execute("CREATE INDEX IF NOT EXISTS drills_retention ON drills(at DESC, id DESC)")
    prune_records(db)
