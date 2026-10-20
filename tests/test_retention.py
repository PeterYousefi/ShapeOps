"""Use isolated persistent SQLite files; never mutate actual local telemetry."""
import sqlite3
import pytest
from backend.retention import (
    prune_records, initialize_retention, REQUEST_MAX_ROWS,
    REQUEST_MAX_AGE_SECONDS, DRILL_MAX_ROWS, DRILL_MAX_AGE_SECONDS,
)


@pytest.fixture
def db(tmp_path):
    with sqlite3.connect(tmp_path / "telemetry.sqlite") as connection:
        for table in ("requests", "drills"):
            connection.execute(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, at REAL, payload TEXT)")
        yield connection


@pytest.mark.parametrize("table,limit,age", [
    ("requests", REQUEST_MAX_ROWS, REQUEST_MAX_AGE_SECONDS),
    ("drills", DRILL_MAX_ROWS, DRILL_MAX_AGE_SECONDS),
])
def test_retention_caps_age_count_and_preserves_latest_payload(db, table, limit, age):
    now = 10000000.0
    db.executemany(f"INSERT INTO {table} VALUES (?,?,?)", [
        (f"{i:05}", now - i, f"original-{i}") for i in range(limit + 50)
    ])
    db.execute(f"INSERT INTO {table} VALUES (?,?,?)", ("expired", now - age - 1, "old"))
    prune_records(db, now=now)
    rows = db.execute(f"SELECT id,payload FROM {table} ORDER BY at DESC, id DESC").fetchall()
    assert rows == [(f"{i:05}", f"original-{i}") for i in range(limit)]
    prune_records(db, now=now)
    assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == limit
    # Expiration works without another insertion, e.g. on a read after an idle period.
    prune_records(db, now=now + age + 1)
    assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_tied_times_have_deterministic_retention(db):
    db.executemany("INSERT INTO drills VALUES (?,?,?)", [
        (f"{i:04}", 1000, "unchanged") for i in range(DRILL_MAX_ROWS + 2)
    ])
    prune_records(db, now=1000)
    ids = [row[0] for row in db.execute("SELECT id FROM drills ORDER BY id")]
    assert ids == [f"{i:04}" for i in range(2, DRILL_MAX_ROWS + 2)]


def test_age_boundary_and_transaction_rollback(db):
    cutoff = 10000000 - DRILL_MAX_AGE_SECONDS
    db.executemany("INSERT INTO drills VALUES (?,?,?)", [
        ("boundary", cutoff, "kept"), ("expired", cutoff - .001, "removed")
    ])
    db.commit()
    prune_records(db, now=10000000)
    assert db.execute("SELECT id FROM drills").fetchall() == [("boundary",)]
    db.rollback()
    assert db.execute("SELECT COUNT(*) FROM drills").fetchone()[0] == 2


def test_startup_reopens_prunes_and_indexes_legacy_database(db):
    db.execute("INSERT INTO requests VALUES ('old',0,'historical')")
    db.commit()
    initialize_retention(db)
    db.commit()
    with sqlite3.connect(db.execute("PRAGMA database_list").fetchone()[2]) as reopened:
        initialize_retention(reopened)
        assert reopened.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
        for table in ("requests", "drills"):
            assert f"{table}_retention" in [row[1] for row in reopened.execute(f"PRAGMA index_list({table})")]
