"""Job isolation and genuine procedural candidate training; not industrial evaluation."""
import json
import pytest
from backend.candidate_job import run_job
from backend.registry import get_run


def test_real_candidate_job_isolated_from_serving_paths(tmp_path, monkeypatch):
    active = tmp_path / 'active'
    active.mkdir()
    sentinel = active / 'sentinel'
    sentinel.write_text('serving-state-fixture')
    monkeypatch.setenv('SHAPEOPS_DATA_DIR', str(active))
    monkeypatch.setenv('SHAPEOPS_REPORT_DIR', str(active))
    result = run_job(tmp_path / 'jobs')
    assert result['status'] == 'succeeded'
    assert result['started_at'] <= result['finished_at']
    candidate = result['candidate']
    assert candidate['stage'] == 'candidate' and candidate['gates']['security'] is False
    directory = tmp_path / 'jobs' / result['id']
    assert json.loads((directory / 'job.json').read_text()) == result
    run = get_run(directory / 'runtime/registry.sqlite', candidate['run_id'])
    assert candidate['package_id'] in {model['package_id'] for model in run['models']}
    package = directory / 'runtime/models/packages-v2' / candidate['package_id']
    assert (package / 'estimator.joblib').is_file()
    assert (directory / 'reports/evaluation.json').is_file()
    from backend.job_history import get_job, list_jobs
    saved = get_job(tmp_path / 'jobs', result['id'])
    assert saved.candidate.package_id == candidate['package_id']
    assert list_jobs(tmp_path / 'jobs')[0].id == result['id']
    assert sorted(path.name for path in active.iterdir()) == ['sentinel']
    assert sentinel.read_text() == 'serving-state-fixture'


def test_timeout_records_terminal_state_and_no_candidate(tmp_path):
    result = run_job(tmp_path / 'jobs', timeout=.001)
    assert result['status'] == 'timed_out' and 'candidate' not in result
    assert json.loads((tmp_path / 'jobs' / result['id'] / 'job.json').read_text()) == result


@pytest.mark.parametrize('timeout', [0, -1, 181, float('nan'), float('inf')])
def test_invalid_budgets_fail_before_creating_job(tmp_path, timeout):
    root = tmp_path / 'jobs'
    with pytest.raises(ValueError):
        run_job(root, timeout)
    assert not root.exists()


def test_worker_start_failure_records_safe_terminal_outcome(tmp_path, monkeypatch):
    import backend.candidate_job as jobs
    def unavailable(*args, **kwargs):
        raise OSError('private fixture diagnostic')
    monkeypatch.setattr(jobs.subprocess, 'Popen', unavailable)
    result = run_job(tmp_path / 'jobs')
    assert result['status'] == 'failed' and 'candidate' not in result
    assert 'private fixture diagnostic' not in str(result)
    assert json.loads((tmp_path / 'jobs' / result['id'] / 'job.json').read_text()) == result


def test_parent_interruption_stops_worker_and_persists_state(tmp_path, monkeypatch):
    import backend.candidate_job as jobs
    signals = []
    class InterruptedProcess:
        pid = 12345
        waits = 0
        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise KeyboardInterrupt
            return -9
        def poll(self):
            return None
    process = InterruptedProcess()
    monkeypatch.setattr(jobs.subprocess, 'Popen', lambda *args, **kwargs: process)
    monkeypatch.setattr(jobs.os, 'killpg', lambda pid, sig: signals.append((pid, sig)))
    with pytest.raises(KeyboardInterrupt):
        run_job(tmp_path / 'jobs')
    assert signals == [(12345, jobs.signal.SIGKILL)] and process.waits == 2
    metadata = list((tmp_path / 'jobs').glob('*/job.json'))
    assert len(metadata) == 1
    assert json.loads(metadata[0].read_text())['status'] == 'interrupted'
