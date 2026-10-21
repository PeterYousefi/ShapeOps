import json
import sqlite3
import subprocess
import sys
import pytest
from starlette.testclient import TestClient

from backend.app import app
from backend.governance import evaluate_gates
from backend.release import (
    list_releases,
    record_release,
    verify_operator_token,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAPEOPS_DATA_DIR", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def test_verify_operator_token(monkeypatch):
    monkeypatch.delenv("SHAPEOPS_OPERATOR_TOKEN", raising=False)
    valid, msg = verify_operator_token(None)
    assert not valid and "not configured" in msg

    monkeypatch.setenv("SHAPEOPS_OPERATOR_TOKEN", "secret-token-12345")
    valid, msg = verify_operator_token(None)
    assert not valid and "Missing" in msg

    valid, msg = verify_operator_token("Basic dXNlcjpwYXNz")
    assert not valid and "Bearer" in msg

    valid, msg = verify_operator_token("Bearer wrong-token")
    assert not valid and "Invalid" in msg

    valid, operator = verify_operator_token("Bearer secret-token-12345")
    assert valid and operator == "authorized-operator"


def test_record_and_list_releases(tmp_path):
    db_path = tmp_path / "releases.sqlite"
    gates = evaluate_gates(0.95, True, True, True)

    rec = record_release(
        db_path,
        "lead-engineer",
        "surface-et-v2",
        "a" * 64,
        gates,
        "approved",
        "Candidate satisfies all production release gates",
    )
    assert rec["operator"] == "lead-engineer"
    assert rec["status"] == "approved"
    assert rec["candidate_id"] == "surface-et-v2"

    history = list_releases(db_path, limit=10)
    assert len(history) == 1
    assert history[0]["id"] == rec["id"]
    assert history[0]["gates"]["quality"] is True

    # Validation errors
    with pytest.raises(ValueError, match="Release status"):
        record_release(
            db_path,
            "lead-engineer",
            "surface-et-v2",
            "a" * 64,
            gates,
            "invalid-status",
            "Rationale",
        )

    with pytest.raises(ValueError, match="Package ID"):
        record_release(
            db_path,
            "lead-engineer",
            "surface-et-v2",
            "short-digest",
            gates,
            "approved",
            "Rationale",
        )


def test_append_only_triggers(tmp_path):
    db_path = tmp_path / "releases.sqlite"
    gates = evaluate_gates(0.95, True, True, True)
    rec = record_release(
        db_path,
        "lead-engineer",
        "surface-et-v2",
        "a" * 64,
        gates,
        "approved",
        "Audit justification",
    )

    conn = sqlite3.connect(db_path)
    try:
        # Trigger aborts UPDATE
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE releases SET status='rejected' WHERE id=?", (rec["id"],))

        # Trigger aborts DELETE
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM releases WHERE id=?", (rec["id"],))
    finally:
        conn.close()


def test_promote_unauthenticated_and_authenticated(client, monkeypatch):
    monkeypatch.delenv("SHAPEOPS_OPERATOR_TOKEN", raising=False)
    # Unauthenticated call must return 403
    res = client.post("/api/operations/promote")
    assert res.status_code == 403
    assert "Production administration is disabled" in res.json()["detail"]

    # Invalid token must return 403
    monkeypatch.setenv("SHAPEOPS_OPERATOR_TOKEN", "prod-operator-token-xyz")
    res = client.post(
        "/api/operations/promote", headers={"Authorization": "Bearer wrong-token"}
    )
    assert res.status_code == 403

    # Authenticated call
    res = client.post(
        "/api/operations/promote",
        headers={"Authorization": "Bearer prod-operator-token-xyz"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "approved"
    assert payload["candidate_id"] == "surface-et-v2"
    assert len(payload["id"]) == 32

    # Query releases endpoint
    history_res = client.get("/api/operations/releases")
    assert history_res.status_code == 200
    releases = history_res.json()["releases"]
    assert len(releases) == 1
    assert releases[0]["id"] == payload["id"]


def test_cli(tmp_path):
    db_path = tmp_path / "releases.sqlite"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.release",
            "evaluate",
            "--database",
            str(db_path),
            "--operator",
            "release-admin",
            "--token",
            "cli-token-abc",
            "--candidate",
            "surface-et-v2",
            "--package-id",
            "b" * 64,
            "--macro-f1",
            "0.92",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    record = json.loads(proc.stdout)
    assert record["status"] == "approved"
    assert record["operator"] == "release-admin"

    # List command
    list_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.release",
            "list",
            "--database",
            str(db_path),
        ],
        capture_output=True,
        text=True,
    )
    assert list_proc.returncode == 0
    items = json.loads(list_proc.stdout)
    assert len(items) == 1
    assert items[0]["id"] == record["id"]
