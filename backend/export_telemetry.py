"""Trusted local, read-only retained telemetry export; no cloud or raw CAD access."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import time

from backend.responses import DriftObservation, RequestRecord
from backend.retention import REQUEST_MAX_AGE_SECONDS, REQUEST_MAX_ROWS

MAX_EXPORT_BYTES = 8 * 1024 * 1024
MAX_DRIFT_BYTES = 16 * 1024
COLUMNS = 'id,at,source,model,success,latency,parse,execution,faces,confidence,ood,error'


def snapshot(database: Path, *, now: float | None = None) -> dict:
    captured_at = time.time() if now is None else now
    if not math.isfinite(captured_at) or captured_at < 0:
        raise ValueError('Invalid snapshot time')
    if not stat.S_ISREG(database.lstat().st_mode):
        raise ValueError('Telemetry database must be a regular file')
    db = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        # A single snapshot binds every request to its screening evidence. No
        # prune/migration is run; even an expired database remains unchanged.
        has_drift = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='drift_observations'").fetchone())
        selected = ','.join(
            f'CASE WHEN length(CAST({key} AS BLOB)) <= 1024 THEN {key} ELSE NULL END AS {key}'
            if key in {'id', 'source', 'model', 'error'} else key for key in COLUMNS.split(',')
        )
        rows = db.execute(
            f'SELECT {selected} '
            'FROM requests WHERE at >= ? AND at <= ? ORDER BY at DESC,id DESC LIMIT ?',
            (captured_at - REQUEST_MAX_AGE_SECONDS, captured_at, REQUEST_MAX_ROWS),
        )
        records = []
        for row in rows:
            request = RequestRecord.model_validate({key: row[key] for key in COLUMNS.split(',')})
            drift = None
            if has_drift:
                # Inspect byte length before materializing potentially corrupt JSON.
                saved = db.execute('SELECT length(CAST(result AS BLOB)),at FROM drift_observations WHERE id=?', (request.id,)).fetchone()
                if saved:
                    if saved[0] is None or not 0 < saved[0] <= MAX_DRIFT_BYTES:
                        raise ValueError('Screening metadata exceeds export budget')
                    raw = db.execute('SELECT result FROM drift_observations WHERE id=?', (request.id,)).fetchone()[0]
                    drift = DriftObservation.model_validate_json(raw)
                    if (not request.success or drift.id != request.id
                            or drift.source != request.source or drift.model != request.model
                            or drift.at != saved[1] or drift.ood != bool(request.ood)):
                        raise ValueError('Screening evidence does not match its request')
            records.append({'request': request.model_dump(), 'screening': drift.model_dump() if drift else None})
        return {
            'schema_version': 1,
            'origin': 'Actual retained local inference telemetry; not production usage',
            'captured_at': captured_at,
            'selection': {'max_rows': REQUEST_MAX_ROWS, 'max_age_seconds': REQUEST_MAX_AGE_SECONDS,
                          'order': 'at descending, id descending', 'cutoff_inclusive': captured_at - REQUEST_MAX_AGE_SECONDS},
            'screening_available': has_drift,
            'records': records,
        }
    finally:
        db.close()


def export(database: Path, output: Path) -> dict:
    value = snapshot(database)
    payload = json.dumps(value, allow_nan=False, sort_keys=True, separators=(',', ':')).encode()
    if len(payload) > MAX_EXPORT_BYTES:
        raise ValueError('Export exceeds total byte budget')
    # Publish complete evidence without overwriting any existing file/symlink.
    # Output parent must already exist; no runtime/schema directories are created.
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
        staging = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            staging.unlink(missing_ok=True)
            raise
    try:
        os.link(staging, output)
    finally:
        staging.unlink(missing_ok=True)
    return {'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload), 'records': len(value['records'])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export(args.database, args.output)
    except (OSError, sqlite3.Error, ValueError):
        parser.exit(1, 'Telemetry export failed; source and existing output were not modified.\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
