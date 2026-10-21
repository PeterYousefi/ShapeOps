"""Failure injection fixtures are not production incidents or evaluation results."""
import sqlite3
import time
import pytest
from backend.registry import record_failure, list_failures, list_runs, connect


def test_failure_journal_is_persistent_append_only_and_separate(tmp_path):
    path = tmp_path / 'registry.sqlite'
    assert list_failures(path) == [] and not path.exists()
    first = record_failure(path, time.time(), 'validation')
    second = record_failure(path, time.time(), 'execution')
    rows = list_failures(path)
    assert [row['id'] for row in rows] == [second, first]
    assert all(row['started_at'] <= row['failed_at'] for row in rows)
    assert list_runs(path) == []
    assert len(list_failures(path, 1)) == 1
    db = connect(path)
    try:
        for sql in ('DELETE FROM training_failures', 'UPDATE training_failures SET category=category'):
            with pytest.raises(sqlite3.IntegrityError, match='append-only'):
                db.execute(sql)
            db.rollback()
    finally:
        db.close()
    assert list_failures(path) == rows


def test_legacy_journal_read_does_not_migrate_or_create_failure_table(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE training_runs(id TEXT PRIMARY KEY,started_at REAL,completed_at REAL)')
    assert list_failures(path) == []
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='training_failures'").fetchone() is None


@pytest.mark.parametrize('limit', [0, -1, 101])
def test_failure_history_limit_validation(tmp_path, limit):
    with pytest.raises(ValueError):
        list_failures(tmp_path / 'absent.sqlite', limit)


@pytest.mark.parametrize('started,category', [(float('nan'), 'execution'), (-1, 'storage'), (float('inf'), 'storage'), (0, 'private traceback')])
def test_failure_metadata_rejects_invalid_input_without_creating_store(tmp_path, started, category):
    path = tmp_path / 'registry.sqlite'
    with pytest.raises(ValueError):
        record_failure(path, started, category)
    assert not path.exists()


@pytest.mark.parametrize('error,category', [(ValueError('private fixture secret'), 'validation'), (OSError('private fixture secret'), 'storage'), (RuntimeError('private fixture secret'), 'execution')])
def test_training_wrapper_records_actual_handled_failure_and_reraises(tmp_path, monkeypatch, error, category):
    from backend import training
    monkeypatch.setenv('SHAPEOPS_DATA_DIR', str(tmp_path))
    def fail():
        raise error
    monkeypatch.setattr(training, '_train', fail)
    with pytest.raises(type(error)) as captured:
        training.train()
    assert captured.value is error
    rows = list_failures(tmp_path / 'registry.sqlite')
    assert len(rows) == 1 and rows[0]['category'] == category
    assert 'private fixture secret' not in str(rows)
    assert set(rows[0]) == {'id', 'started_at', 'failed_at', 'category'}


def test_failure_journal_error_preserves_original_failure(monkeypatch, caplog):
    from backend import training
    error = RuntimeError('original fixture failure')
    def fail():
        raise error
    def unavailable(*args):
        raise OSError('fixture storage unavailable')
    monkeypatch.setattr(training, '_train', fail)
    monkeypatch.setattr(training, 'record_failure', unavailable)
    with pytest.raises(RuntimeError) as captured:
        training.train()
    assert captured.value is error
    assert 'Failed to persist baseline initialization failure' in caplog.text
    assert 'fixture storage unavailable' not in caplog.text


def test_successful_wrapper_preserves_result_and_does_not_record_failure(tmp_path, monkeypatch):
    from backend import training
    result = object()
    monkeypatch.setenv('SHAPEOPS_DATA_DIR', str(tmp_path))
    monkeypatch.setattr(training, '_train', lambda: result)
    assert training.train() is result
    assert not (tmp_path / 'registry.sqlite').exists()


@pytest.mark.parametrize('changes', [{'failed_at': 0.0}, {'started_at': float('nan')}, {'category': 'traceback'}, {'diagnostics': 'private'}])
def test_failure_response_contract_rejects_invalid_records(changes):
    from pydantic import ValidationError
    from backend.responses import TrainingFailure
    fixture = {'id': 'a' * 32, 'started_at': 1.0, 'failed_at': 2.0, 'category': 'validation'}
    with pytest.raises(ValidationError):
        TrainingFailure.model_validate({**fixture, **changes})
