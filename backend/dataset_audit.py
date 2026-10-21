"""Audit a trusted local annotated evaluation corpus; no industrial-accuracy claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Annotated, Literal, Self
from pydantic import Field, model_validator
from backend.contracts import Surface
from backend.responses import OutputModel, Digest

MAX_MANIFEST_BYTES = 64 * 1024
MAX_PART_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024


class FaceAnnotation(OutputModel):
    face_id: Annotated[int, Field(ge=0, le=599)]
    label: Surface


class EvaluationPart(OutputModel):
    path: Annotated[str, Field(min_length=1)]
    sha256: Digest
    group: Annotated[str, Field(min_length=1)]
    faces: Annotated[list[FaceAnnotation], Field(min_length=1, max_length=600)]

    @model_validator(mode='after')
    def safe_path_and_labels(self) -> Self:
        path = Path(self.path)
        if path.is_absolute() or '..' in path.parts or path.suffix.lower() not in {'.step', '.stp'}:
            raise ValueError('Dataset part path must be a contained relative STEP path')
        if [face.face_id for face in self.faces] != list(range(len(self.faces))):
            raise ValueError('Annotations must preserve every original contiguous face ID')
        return self


class EvaluationDataset(OutputModel):
    schema_version: Literal[1]
    name: Annotated[str, Field(min_length=1)]
    source: Annotated[str, Field(min_length=1)]
    license: Annotated[str, Field(min_length=1)]
    rights_evidence: Annotated[str, Field(min_length=1)]
    evaluation_only: bool
    parts: Annotated[list[EvaluationPart], Field(min_length=1, max_length=20)]

    @model_validator(mode='after')
    def distinct_evaluation_inputs(self) -> Self:
        if self.evaluation_only is not True:
            raise ValueError('This manifest is evaluation-only')
        if len({part.path for part in self.parts}) != len(self.parts) or len({part.sha256 for part in self.parts}) != len(self.parts):
            raise ValueError('Dataset contains duplicate paths or content')
        return self


def read_regular(path: Path, limit: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('Dataset input must be a regular file')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        if not data or len(data) > limit:
            raise ValueError('Dataset input is empty or exceeds its byte budget')
        return data
    finally:
        os.close(descriptor)


def load_dataset(manifest: Path) -> tuple[EvaluationDataset, str]:
    payload = read_regular(manifest, MAX_MANIFEST_BYTES)
    dataset = EvaluationDataset.model_validate_json(payload)
    return dataset, hashlib.sha256(payload).hexdigest()


def validated_inputs(manifest: Path) -> tuple[EvaluationDataset, str, list[tuple[EvaluationPart, bytes]]]:
    dataset, manifest_hash = load_dataset(manifest)
    root = manifest.parent.resolve()
    inputs: list[tuple[EvaluationPart, bytes]] = []
    total = 0
    # Check the complete corpus before invoking expensive native parsing.
    for part in dataset.parts:
        path = root / part.path
        if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root and root in parent.parents):
            raise ValueError('Dataset paths must not traverse symlinks')
        if not path.resolve().is_relative_to(root):
            raise ValueError('Dataset part escaped its corpus root')
        data = read_regular(path, MAX_PART_BYTES)
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError('Dataset exceeds aggregate byte budget')
        if hashlib.sha256(data).hexdigest() != part.sha256:
            raise ValueError('Dataset part checksum mismatch')
        inputs.append((part, data))
    return dataset, manifest_hash, inputs


def audit_dataset(manifest: Path) -> dict:
    dataset, manifest_hash, inputs = validated_inputs(manifest)
    total = sum(len(data) for _, data in inputs)
    from backend.app import process_step  # Reuse genuine bounded disposable CAD worker.
    results: list[dict] = []
    for part, data in inputs:
        geometry = process_step(data)
        if len(part.faces) != geometry['face_count']:
            raise ValueError('Dataset annotations do not match parsed face IDs')
        results.append({'path': part.path, 'sha256': part.sha256, 'group': part.group,
                        'face_count': geometry['face_count']})
    return {'scope': 'Local evaluation-corpus input audit only; no model performance or legal verification.',
            'name': dataset.name, 'manifest_sha256': manifest_hash, 'parts': results,
            'total_bytes': total, 'total_faces': sum(part['face_count'] for part in results)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit_dataset(args.manifest), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
