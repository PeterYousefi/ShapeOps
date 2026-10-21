"""Isolated SQLite fixtures are test data, never production telemetry."""
import hashlib
import json
import sqlite3
import time

import pytest

from backend.export_telemetry import export, snapshot
from backend.retention import REQUEST_MAX_AGE_SECONDS


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'telemetry ?#.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE requests (id TEXT PRIMARY KEY, at REAL, source TEXT, model TEXT, success INTEGER, latency REAL, parse REAL, execution REAL, faces INTEGER, confidence REAL, ood INTEGER, error TEXT)')
        db.execute('CREATE TABLE drift_observations (id TEXT PRIMARY KEY,at REAL,result TEXT)')
    return path


def insert(database, identity='a' * 32, at=None, **values):
    row = {'id': identity, 'at': time.time() if at is None else at, 'source': 'sample', 'model': 'surface-rf-v1',
           'success': 1, 'latency': 2.0, 'parse': 0.0, 'execution': 1.0, 'faces': 3, 'confidence': .9, 'ood': 0, 'error': ''}
    row.update(values)
    with sqlite3.connect(database) as db:
        db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', tuple(row.values()))


def screening(identity='a' * 32, model='surface-rf-v1'):
    return {'id': identity, 'at': 100.0, 'source': 'sample', 'model': model, 'reference_id': 'b' * 64,
            'reference_scope': 'Owned procedural sample geometries; screening only', 'reference_parts': 5,
            'threshold': 3.0, 'warning': False, 'ood_score': -0.1, 'ood': False,
            'features': [{'name': 'face_count', 'value': 3.0, 'reference_mean': 3.0, 'reference_scale': 1.0, 'deviation': 0.0}]}


def save_screening(database, value):
    with sqlite3.connect(database) as db:
        db.execute('INSERT INTO drift_observations VALUES (?,?,?)', ('a' * 32, 100, json.dumps(value)))


def test_exact_records_reference_and_hash_without_source_changes(database, tmp_path):
    insert(database)
    value = screening()
    save_screening(database, value)
    before = database.read_bytes()
    output = tmp_path / 'evidence.json'
    result = export(database, output)
    payload = output.read_bytes()
    records = json.loads(payload)['records']
    assert records[0]['screening'] == value
    assert records[0]['request']['faces'] == 3
    assert result == {'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload), 'records': 1}
    assert database.read_bytes() == before
    assert output.stat().st_mode & 0o777 == 0o600


def test_retention_boundary_order_limit_no_pruning(database):
    now = 10000000.0
    cutoff = now - REQUEST_MAX_AGE_SECONDS
    insert(database, 'old', cutoff - 1)
    insert(database, 'future', now + 1)
    insert(database, 'boundary', cutoff)
    assert [r['request']['id'] for r in snapshot(database, now=now)['records']] == ['boundary']
    with sqlite3.connect(database) as db:
        for i in range(1002):
            db.execute('INSERT INTO requests SELECT ?,?,?,?,?,?,?,?,?,?,?,?', (f'{i:04}', now, 'sample', 'surface-rf-v1', 1, 0, 0, 0, 3, .9, 0, ''))
    rows = snapshot(database, now=now)['records']
    assert len(rows) == 1000
    assert rows[0]['request']['id'] == '1001'
    assert rows[-1]['request']['id'] == '0002'
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT count(*) FROM requests').fetchone()[0] == 1005


def test_empty_and_legacy_no_backfill(database):
    with sqlite3.connect(database) as db:
        db.execute('DROP TABLE drift_observations')
    assert snapshot(database)['records'] == []
    insert(database)
    result = snapshot(database)
    assert result['screening_available'] is False
    assert result['records'][0]['screening'] is None


@pytest.mark.parametrize('field,value', [('confidence', 2), ('latency', -1), ('source', 'invented'), ('model', 'x' * 1025)])
def test_invalid_request_fails_without_publishing(database, tmp_path, field, value):
    insert(database, **{field: value})
    with pytest.raises(ValueError):
        export(database, tmp_path / 'out.json')
    assert not (tmp_path / 'out.json').exists()


@pytest.mark.parametrize('change', [{'model': 'different'}, {'id': 'c' * 32}, {'warning': True}, {'at': 101.0}, {'ood': True, 'ood_score': .1}])
def test_corrupt_or_mismatched_screening_fails(database, change):
    insert(database)
    save_screening(database, {**screening(), **change})
    with pytest.raises(ValueError):
        snapshot(database)


def test_failed_request_cannot_carry_success_screening(database):
    insert(database, success=0)
    save_screening(database, screening())
    with pytest.raises(ValueError):
        snapshot(database)


def test_oversized_screening_and_total_budget(database, tmp_path, monkeypatch):
    insert(database)
    save_screening(database, {'padding': 'x' * 17000})
    with pytest.raises(ValueError, match='budget'):
        snapshot(database)
    with sqlite3.connect(database) as db:
        db.execute('DELETE FROM drift_observations')
    monkeypatch.setattr('backend.export_telemetry.MAX_EXPORT_BYTES', 1)
    with pytest.raises(ValueError, match='budget'):
        export(database, tmp_path / 'out.json')
    assert not (tmp_path / 'out.json').exists()


def test_existing_outputs_and_missing_input_are_never_replaced(database, tmp_path):
    output = tmp_path / 'existing'
    output.write_text('preserve')
    with pytest.raises(FileExistsError):
        export(database, output)
    assert output.read_text() == 'preserve'
    link = tmp_path / 'link'
    link.symlink_to(output)
    with pytest.raises(FileExistsError):
        export(database, link)
    assert output.read_text() == 'preserve'
    missing = tmp_path / 'missing.sqlite'
    with pytest.raises(FileNotFoundError):
        snapshot(missing)
    assert not missing.exists()
    link.unlink()
    link.symlink_to(database)
    with pytest.raises(ValueError):
        snapshot(link)


def test_snapshot_stays_consistent_when_another_writer_commits(database, monkeypatch):
    insert(database)
    save_screening(database, screening())
    connect = sqlite3.connect
    with connect(database) as db:
        db.execute('PRAGMA journal_mode=WAL')
    changed = False

    def reader(*args, **kwargs):
        db = connect(*args, **kwargs)

        def concurrent_write(sql):
            nonlocal changed
            if 'SELECT length(CAST(result' in sql and not changed:
                changed = True
                with connect(database) as writer:
                    writer.execute("UPDATE requests SET model='new-model'")
                    writer.execute('UPDATE drift_observations SET result=?', (json.dumps(screening(model='new-model')),))
        db.set_trace_callback(concurrent_write)
        return db

    monkeypatch.setattr('backend.export_telemetry.sqlite3.connect', reader)
    result = snapshot(database)
    assert changed
    assert result['records'][0]['request']['model'] == 'surface-rf-v1'
    assert result['records'][0]['screening']['model'] == 'surface-rf-v1'
    with connect(database) as db:
        assert db.execute('SELECT model FROM requests').fetchone()[0] == 'new-model'


def test_publication_failure_cleans_staging_and_preserves_source(database, tmp_path, monkeypatch):
    before = set(tmp_path.iterdir())
    original = database.read_bytes()

    def fail(*args):
        raise OSError('filesystem unavailable')

    monkeypatch.setattr('backend.export_telemetry.os.link', fail)
    with pytest.raises(OSError):
        export(database, tmp_path / 'out.json')
    assert set(tmp_path.iterdir()) == before
    assert database.read_bytes() == original
