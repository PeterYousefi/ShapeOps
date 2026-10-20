"""Synthetic journal fixtures are explicitly not completed inference/production data."""
import hashlib
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.registry import record_run, list_runs, get_run, connect


def record(model="fixture"):
    manifest = {"id": model, "git_commit": "unit-fixture", "checksum": "unit-fixture"}
    identity = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**manifest, "package_id": identity}


def test_repeated_training_preserves_distinct_executions_and_snapshots(tmp_path):
    path = tmp_path / "registry.sqlite"
    assert list_runs(path) == [] and get_run(path, "missing") is None
    original = record()
    first = record_run(path, time.time(), [original])
    second = record_run(path, time.time(), [original])
    assert first != second
    assert [r["id"] for r in list_runs(path)] == [second, first]
    assert get_run(path, first)["models"] == [original]
    assert len(list_runs(path, 1)) == 1
    assert get_run(path, "' OR 1=1 --") is None


def test_journal_rejects_updates_deletions_and_orphans(tmp_path):
    path = tmp_path / "registry.sqlite"
    run_id = record_run(path, time.time(), [record()])
    db = connect(path)
    try:
        for table in ("training_runs", "run_models"):
            for sql in (f"DELETE FROM {table}", f"UPDATE {table} SET {'id=id' if table == 'training_runs' else 'model_id=model_id'}"):
                with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                    db.execute(sql)
                db.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO run_models VALUES ('absent','fixture','hash','{}')")
        db.rollback()
    finally:
        db.close()
    assert get_run(path, run_id)["models"] == [record()]


def test_failed_run_does_not_leave_partial_history(tmp_path):
    path = tmp_path / "registry.sqlite"
    successful = record_run(path, time.time(), [record()])
    # Duplicate model IDs fail inside the transaction after the run row is inserted.
    with pytest.raises(sqlite3.IntegrityError):
        record_run(path, time.time(), [record(), record()])
    assert [r["id"] for r in list_runs(path)] == [successful]
    with pytest.raises(ValueError):
        record_run(path, time.time(), [{**record(), "git_commit": "tampered"}])
    with pytest.raises(ValueError):
        record_run(path, time.time() + 3600, [record()])
    with pytest.raises(ValueError):
        record_run(path, time.time(), [])
    assert len(list_runs(path)) == 1


def test_concurrent_training_runs_are_atomic_after_reopen(tmp_path):
    path = tmp_path / "registry.sqlite"
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: record_run(path, time.time(), [record("a"), record("b")]), range(8)))
    assert len(set(ids)) == 8
    assert {r["id"] for r in list_runs(path)} == set(ids)
    assert all(len(get_run(path, identity)["models"]) == 2 for identity in ids)


def test_bounded_read_limits(tmp_path):
    for limit in (0, -1, 101):
        with pytest.raises(ValueError):
            list_runs(tmp_path / "absent.sqlite", limit)
