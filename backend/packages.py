"""Content-addressed local packages; never load untrusted serialized estimators."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


def publish_package(root: Path, trees: bytes, estimator: bytes, record: dict) -> str:
    """Publish a complete package atomically, or verify and reuse identical bytes."""
    if (record.get("checksum") != hashlib.sha256(trees).hexdigest()
            or record.get("package_checksum") != hashlib.sha256(estimator).hexdigest()):
        raise ValueError("Model package checksum mismatch")
    manifest = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    package_id = hashlib.sha256(manifest).hexdigest()
    # Versioned layout leaves historical tree-hash directories untouched.
    parent = root / "packages-v2"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / package_id
    files = {"trees.json": trees, "estimator.joblib": estimator, "manifest.json": manifest}

    def verify():
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError("Immutable model package is not a directory")
        if {path.name for path in destination.iterdir()} != set(files):
            raise ValueError("Immutable model package is incomplete or modified")
        for name, expected in files.items():
            path = destination / name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
                raise ValueError("Immutable model package integrity check failed")

    if destination.exists() or destination.is_symlink():
        verify()
        return package_id
    with tempfile.TemporaryDirectory(prefix=".publish-", dir=parent) as temporary:
        staging = Path(temporary) / "package"
        staging.mkdir()
        for name, data in files.items():
            with (staging / name).open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        try:
            staging.rename(destination)
        except OSError:
            # A concurrent publisher may have won; only reuse an exact package.
            if not destination.exists():
                raise
            verify()
    verify()
    return package_id
