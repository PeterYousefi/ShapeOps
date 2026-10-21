"""Explicit synthetic job metadata tests; no production training history is invented."""
import json
import os
import pytest
from pydantic import ValidationError
from backend.job_history import get_job, list_jobs

SCOPE = 'Isolated local procedural baseline candidate. No serving or production mutation.'


def fixture(root, identity='a' * 32, **changes):
    directory = root / identity
    directory.mkdir(parents=True, exist_ok=True)
    payload = {'id': identity, 'started_at': 1.0, 'status': 'running', 'scope': SCOPE, **changes}
    (directory / 'job.json').write_text(json.dumps(payload))
    return payload


def test_missing_history_never_creates_paths_and_unknown_ids_are_safe(tmp_path):
    root = tmp_path / 'absent'
    assert list_jobs(root) == [] and get_job(root, 'a' * 32) is None
    for identity in ('../../secret', 'invalid', 'A' * 32):
        assert get_job(root, identity) is None
    assert not root.exists()


def test_recent_history_is_sorted_bounded_and_round_trips_after_reopen(tmp_path):
    fixture(tmp_path, 'a' * 32, started_at=2.0)
    fixture(tmp_path, 'b' * 32, started_at=2.0, status='failed', finished_at=3.0)
    fixture(tmp_path, 'c' * 32, started_at=1.0, status='timed_out', finished_at=4.0)
    (tmp_path / 'unrelated').write_text('not metadata')
    (tmp_path / ('d' * 32)).mkdir()  # Reserved directory without first atomic write.
    assert [job.id for job in list_jobs(tmp_path, 2)] == ['b' * 32, 'a' * 32]
    assert get_job(tmp_path, 'b' * 32).status == 'failed'
    assert len(list_jobs(tmp_path)) == 3


@pytest.mark.parametrize('changes', [
    {'status': 'succeeded', 'finished_at': 2.0}, {'status': 'failed'},
    {'status': 'running', 'finished_at': 2.0}, {'status': 'failed', 'finished_at': 0.0},
    {'started_at': float('nan')}, {'diagnostics': 'private'}, {'scope': 'production'},
])
def test_invalid_saved_states_fail_closed(tmp_path, changes):
    fixture(tmp_path, **changes)
    for read in (lambda: list_jobs(tmp_path), lambda: get_job(tmp_path, 'a' * 32)):
        with pytest.raises(ValidationError):
            read()


def test_mismatched_identity_and_oversized_metadata_fail_closed(tmp_path):
    fixture(tmp_path)
    path = tmp_path / ('a' * 32) / 'job.json'
    payload = json.loads(path.read_text())
    payload['id'] = 'b' * 32
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='identity'):
        get_job(tmp_path, 'a' * 32)
    path.write_bytes(b' ' * (64 * 1024 + 1))
    with pytest.raises(ValueError, match='budget'):
        get_job(tmp_path, 'a' * 32)


def test_metadata_symlinks_and_fifo_are_never_read(tmp_path):
    fixture(tmp_path)
    directory = tmp_path / ('a' * 32)
    path = directory / 'job.json'
    original = path.read_bytes()
    path.unlink()
    target = tmp_path / 'other.json'
    target.write_bytes(original)
    path.symlink_to(target)
    with pytest.raises(OSError):
        get_job(tmp_path, 'a' * 32)
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(ValueError, match='regular file'):
        get_job(tmp_path, 'a' * 32)


def test_root_and_job_directory_symlinks_are_rejected(tmp_path):
    root = tmp_path / 'jobs'
    fixture(root)
    alias = tmp_path / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        list_jobs(alias)
    (root / ('b' * 32)).symlink_to(root / ('a' * 32), target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        get_job(root, 'b' * 32)


def test_discovery_cap_requires_explicit_archival(tmp_path, monkeypatch):
    import backend.job_history as history
    monkeypatch.setattr(history, 'MAX_DISCOVERED_JOBS', 2)
    for n in range(3):
        (tmp_path / f'unrelated-{n}').touch()
    with pytest.raises(ValueError, match='archival'):
        list_jobs(tmp_path)


@pytest.mark.parametrize('limit', [0, -1, 101])
def test_history_limit_validation(tmp_path, limit):
    with pytest.raises(ValueError):
        list_jobs(tmp_path, limit)
