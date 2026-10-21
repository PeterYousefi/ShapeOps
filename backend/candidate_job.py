"""Trusted local candidate job; never changes serving models or authorizes release."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from backend.responses import RegisteredModel

MAX_SECONDS = 180
MAX_RESULT_BYTES = 64 * 1024


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(value, allow_nan=False, indent=2))
    temporary.replace(path)


def worker(directory: Path) -> None:
    # The parent supplies fresh job-local paths before importing training/native CAD.
    from backend.training import train
    _, records, _, _ = train()
    candidates = [record for record in records if record['stage'] == 'candidate']
    if len(candidates) != 1:
        raise ValueError('Expected one local candidate')
    candidate = RegisteredModel.model_validate(candidates[0])
    _write(directory / 'candidate.json', candidate.model_dump())


def _stop(process) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # The group may exit between timeout detection and signalling.
    process.wait()


def run_job(root: Path, timeout: float = 120) -> dict:
    if not math.isfinite(timeout) or not 0 < timeout <= MAX_SECONDS:
        raise ValueError('Candidate timeout must be positive and at most 180 seconds')
    identity = uuid.uuid4().hex
    directory = root.resolve() / identity
    directory.mkdir(parents=True, exist_ok=False)
    result = {'id': identity, 'started_at': time.time(), 'status': 'running',
              'scope': 'Isolated local procedural baseline candidate. No serving or production mutation.'}
    _write(directory / 'job.json', result)
    environment = {**os.environ, 'SHAPEOPS_DATA_DIR': str(directory / 'runtime'),
                   'SHAPEOPS_REPORT_DIR': str(directory / 'reports'),
                   'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, '-m', 'backend.candidate_job', '--worker', str(directory)],
            cwd=Path(__file__).resolve().parents[1], env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _stop(process)
            result['status'] = 'timed_out'
        else:
            if code != 0:
                result['status'] = 'failed'
            else:
                with (directory / 'candidate.json').open('rb') as stream:
                    payload = stream.read(MAX_RESULT_BYTES + 1)
                if len(payload) > MAX_RESULT_BYTES:
                    raise ValueError('Candidate result exceeds job result budget')
                candidate = RegisteredModel.model_validate_json(payload)
                if candidate.stage != 'candidate':
                    raise ValueError('Worker returned a non-candidate model')
                result.update(status='succeeded', candidate=candidate.model_dump())
    except (OSError, ValueError):
        result['status'] = 'failed'
    except BaseException:
        if process is not None and process.poll() is None:
            _stop(process)
        result.update(status='interrupted', finished_at=time.time())
        _write(directory / 'job.json', result)
        raise
    result['finished_at'] = time.time()
    _write(directory / 'job.json', result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.runtime/candidate-jobs'))
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        worker(args.worker)
        return 0
    result = run_job(args.output, args.timeout)
    print(json.dumps(result, allow_nan=False, indent=2))
    return 0 if result['status'] == 'succeeded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
