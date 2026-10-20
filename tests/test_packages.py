"""Package bytes in these unit fixtures are not executable model artifacts."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import pytest
from backend.packages import publish_package


def inputs():
    trees, estimator = b'{"trees":[]}', b"unit-fixture-not-a-model"
    record = {"id": "unit-fixture", "checksum": hashlib.sha256(trees).hexdigest(),
              "package_checksum": hashlib.sha256(estimator).hexdigest(), "git_commit": "first"}
    return trees, estimator, record


def test_identical_publication_is_immutable_and_provenance_gets_new_identity(tmp_path):
    trees, estimator, record = inputs()
    first = publish_package(tmp_path, trees, estimator, record)
    directory = tmp_path / "packages-v2" / first
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()}
    assert publish_package(tmp_path, trees, estimator, record) == first
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()}
    second = publish_package(tmp_path, trees, estimator, {**record, "git_commit": "second"})
    assert first != second
    assert json.loads((directory / "manifest.json").read_bytes())["git_commit"] == "first"
    assert {p.name for p in (tmp_path / "packages-v2").iterdir()} == {first, second}


@pytest.mark.parametrize("damage", ["trees", "estimator", "manifest", "missing", "extra", "symlink"])
def test_existing_corruption_is_rejected_without_repair(tmp_path, damage):
    trees, estimator, record = inputs()
    identity = publish_package(tmp_path, trees, estimator, record)
    directory = tmp_path / "packages-v2" / identity
    if damage in {"trees", "estimator", "manifest"}:
        name = {"trees": "trees.json", "estimator": "estimator.joblib", "manifest": "manifest.json"}[damage]
        (directory / name).write_bytes(b"corrupt")
    elif damage == "missing":
        (directory / "trees.json").unlink()
    elif damage == "extra":
        (directory / "unexpected").touch()
    else:
        (directory / "trees.json").unlink()
        target = tmp_path / "elsewhere"
        target.write_bytes(trees)
        (directory / "trees.json").symlink_to(target)
    before = {p.name: p.lstat().st_mtime_ns for p in directory.iterdir()}
    with pytest.raises(ValueError, match="Immutable"):
        publish_package(tmp_path, trees, estimator, record)
    assert before == {p.name: p.lstat().st_mtime_ns for p in directory.iterdir()}


def test_concurrent_publishers_reuse_one_complete_package(tmp_path):
    with ThreadPoolExecutor(max_workers=4) as pool:
        identities = list(pool.map(lambda _: publish_package(tmp_path, *inputs()), range(8)))
    assert len(set(identities)) == 1
    assert [p.name for p in (tmp_path / "packages-v2").iterdir()] == [identities[0]]


def test_failed_staging_cleans_temporary_files_and_publishes_nothing(tmp_path, monkeypatch):
    original = Path.open

    def fail(path, *args, **kwargs):
        if path.name == "estimator.joblib":
            raise OSError("injected storage failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail)
    with pytest.raises(OSError):
        publish_package(tmp_path, *inputs())
    assert list((tmp_path / "packages-v2").iterdir()) == []


def test_mismatched_or_nonfinite_manifest_is_not_published(tmp_path):
    trees, estimator, record = inputs()
    with pytest.raises(ValueError, match="checksum"):
        publish_package(tmp_path, trees, b"modified", record)
    with pytest.raises(ValueError):
        publish_package(tmp_path, trees, estimator, {**record, "metric": float("nan")})
    assert not (tmp_path / "packages-v2").exists()
