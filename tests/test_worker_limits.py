import errno
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
from types import SimpleNamespace
import pytest
from backend import worker_limits
from backend.worker import write_result


def probe(code):
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=8
    )


def test_child_cpu_budget_is_enforced():
    child = probe(
        "from backend.worker_limits import apply_limits; apply_limits(cpu_seconds=1)\nwhile True: pass"
    )
    assert child.returncode in (-signal.SIGKILL, -signal.SIGXCPU)


def test_child_file_budget_is_enforced(tmp_path):
    code = f"""from backend.worker_limits import apply_limits
import errno
apply_limits(result_bytes=512)
try:
    with open({str(tmp_path / "bounded")!r}, 'wb') as stream: stream.write(b'x'*1024)
except OSError as error:
    assert error.errno == {errno.EFBIG}
    print('ENFORCED')
"""
    child = probe(code)
    assert child.returncode == 0 and "ENFORCED" in child.stdout
    assert (tmp_path / "bounded").stat().st_size <= 512


@pytest.mark.skipif(
    sys.platform != "linux", reason="Address-space enforcement is Linux-specific"
)
def test_child_memory_budget_is_enforced():
    child = probe("""from backend.worker_limits import apply_limits
apply_limits(address_space_bytes=128*1024*1024)
try: allocation = bytearray(256*1024*1024)
except MemoryError: print('ENFORCED')
""")
    assert child.returncode == 0 and "ENFORCED" in child.stdout


def test_inherited_stricter_limits_are_not_relaxed(monkeypatch):
    calls = []
    monkeypatch.setattr(resource, "getrlimit", lambda kind: (2, 3))
    monkeypatch.setattr(
        resource, "setrlimit", lambda kind, value: calls.append((kind, value))
    )
    worker_limits.apply_limits()
    assert all(soft <= 2 and hard <= 3 for _, (soft, hard) in calls)
    assert (resource.RLIMIT_CORE, (0, 0)) in calls


def test_result_is_finite_atomic_and_bounded(tmp_path, monkeypatch):
    from backend import worker

    output = tmp_path / "result.json"
    write_result({"faces": [1, 2]}, output)
    assert json.loads(output.read_bytes()) == {"faces": [1, 2]}
    with pytest.raises(ValueError):
        write_result({"value": float("nan")}, output)
    assert json.loads(output.read_bytes()) == {"faces": [1, 2]}
    monkeypatch.setattr(worker, "MAX_RESULT_BYTES", 32)
    with pytest.raises(ValueError):
        write_result({"value": "x" * 100}, output)
    assert not output.with_suffix(".partial").exists()


@pytest.mark.parametrize(
    "mode", ["missing", "invalid", "oversized", "exit", "array", "symlink", "fifo"]
)
def test_parent_rejects_bad_worker_results(mode, monkeypatch):
    import backend.app as module

    directories = []

    def run(command, **options):
        assert options["stdout"] == subprocess.DEVNULL
        assert options["stderr"] == subprocess.DEVNULL
        assert options["env"]["OPENBLAS_NUM_THREADS"] == "1"
        output = Path(command[-1])
        directories.append(output.parent)
        if mode == "symlink":
            target = output.parent / "not-a-result.json"
            target.write_bytes(b"{}")
            output.symlink_to(target)
        if mode == "fifo":
            os.mkfifo(output)
        if mode == "invalid":
            output.write_bytes(b"{")
        if mode == "oversized":
            output.write_bytes(b"x" * (worker_limits.MAX_RESULT_BYTES + 1))
        if mode == "array":
            output.write_bytes(b"[]")
        return SimpleNamespace(returncode=2 if mode == "exit" else 0)

    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(ValueError, match="resource limits"):
        module.process_step(b"ISO-10303-21;")

    assert directories and all(not directory.exists() for directory in directories)
