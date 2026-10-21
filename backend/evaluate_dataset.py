"""Isolated evaluation on supplied labels; no serving mutation or release authority."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import get_args
from collections.abc import Sequence
import numpy as np
from backend.candidate_job import _stop
from backend.contracts import Surface
from backend.dataset_audit import read_regular, validated_inputs

MAX_REPORT_BYTES = 256 * 1024
LABELS = list(get_args(Surface))


def summarize(truth: Sequence[str], predictions: Sequence[str], probabilities: list[list[float]]) -> dict:
    matrix = np.asarray(probabilities, dtype=float)
    n = len(truth)
    if (not n or len(predictions) != n or matrix.shape != (n, len(LABELS))
            or not np.isfinite(matrix).all() or (matrix < 0).any() or (matrix > 1).any()
            or not np.allclose(matrix.sum(axis=1), 1, atol=1e-8, rtol=0)):
        raise ValueError('Evaluation probabilities and observation counts must be valid')
    if any(label not in LABELS for label in [*truth, *predictions]):
        raise ValueError('Unsupported evaluation label')
    if any(row[LABELS.index(prediction)] != max(row) for row, prediction in zip(matrix, predictions)):
        raise ValueError('Prediction must match maximum probability')
    confusion = {label: {predicted: 0 for predicted in LABELS} for label in LABELS}
    for actual, predicted in zip(truth, predictions):
        confusion[actual][predicted] += 1
    per_class = {}
    f1s = []
    for label in LABELS:
        support_count = sum(confusion[label].values())
        prediction_count = sum(row[label] for row in confusion.values())
        tp = confusion[label][label]
        f1 = 2 * tp / (support_count + prediction_count) if support_count + prediction_count else None
        if f1 is not None:
            f1s.append(f1)
        per_class[label] = {'support': support_count, 'predicted': prediction_count, 'f1': f1}
    correct = np.asarray([actual == predicted for actual, predicted in zip(truth, predictions)])
    confidence = matrix.max(axis=1)
    bins = []
    ece = 0.0
    # Equal-width bins; confidence=1 belongs to the final bin.
    assignments = np.minimum((confidence * 10).astype(int), 9)
    for index in range(10):
        selected = assignments == index
        count = int(selected.sum())
        accuracy = float(correct[selected].mean()) if count else None
        mean = float(confidence[selected].mean()) if count else None
        if accuracy is not None and mean is not None:
            ece += count / n * abs(accuracy - mean)
        bins.append({'lower': index / 10, 'upper': (index + 1) / 10,
                     'count': count, 'accuracy': accuracy, 'confidence': mean})
    one_hot = np.zeros_like(matrix)
    one_hot[np.arange(n), [LABELS.index(label) for label in truth]] = 1
    return {'observations': n, 'accuracy': float(correct.mean()), 'macro_f1_observed': sum(f1s) / len(f1s),
            'confusion': confusion, 'per_class': per_class, 'calibration_bins': bins,
            'ece_10_bins': ece, 'multiclass_brier': float(np.square(matrix - one_hot).sum(axis=1).mean())}


def worker(manifest: Path, output: Path) -> None:
    dataset, digest, inputs = validated_inputs(manifest)
    from backend.training import train
    from backend.app import process_step
    models, records, _, _ = train()
    observations = []
    parts = []
    for part, data in inputs:
        geometry = process_step(data)
        if len(part.faces) != geometry['face_count']:
            raise ValueError('Evaluation annotation count does not match parsed faces')
        for annotation, face in zip(part.faces, geometry['faces']):
            if annotation.face_id != face['id']:
                raise ValueError('Original face identity changed during evaluation')
            observations.append((annotation.label, face['features']))
        parts.append({'path': part.path, 'sha256': part.sha256, 'group': part.group, 'faces': geometry['face_count']})
    truth = [row[0] for row in observations]
    features = np.asarray([row[1] for row in observations])
    results = []
    for record in records:
        model = models[record['id']]
        raw = model.predict_proba(features)
        probabilities = np.zeros((len(truth), len(LABELS)))
        for column, label in enumerate(model.classes_):
            probabilities[:, LABELS.index(label)] = raw[:, column]
        predictions = model.predict(features).tolist()
        results.append({'model': record, 'metrics': summarize(truth, predictions, probabilities.tolist())})
    report = {'scope': 'Supplied annotated corpus only; no industrial generalization, rights verification or release approval.',
              'evaluation_source_sha256': hashlib.sha256(b''.join((Path(__file__).parent / name).read_bytes() for name in ('evaluate_dataset.py', 'dataset_audit.py', 'contracts.py'))).hexdigest(),
              'dataset': dataset.name, 'source': dataset.source, 'license': dataset.license,
              'rights_evidence': dataset.rights_evidence, 'manifest_sha256': digest, 'parts': parts,
              'calibration': 'Diagnostics on uncalibrated models; no calibration fitting.', 'models': results}
    encoded = json.dumps(report, allow_nan=False, indent=2).encode()
    if len(encoded) > MAX_REPORT_BYTES:
        raise ValueError('Evaluation report exceeds bounded result size')
    output.write_bytes(encoded)


def run_evaluation(manifest: Path, output: Path, timeout: float = 180) -> dict:
    if not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise ValueError('Evaluation timeout must be positive and at most 300 seconds')
    # Validate before starting training; the child repeats checks against exact bytes.
    validated_inputs(manifest)
    if output.exists():
        raise FileExistsError('Evaluation output already exists')
    with tempfile.TemporaryDirectory(prefix='shapeops-evaluation-') as temporary:
        directory = Path(temporary)
        report = directory / 'report.json'
        environment = {**os.environ, 'SHAPEOPS_DATA_DIR': str(directory / 'runtime'),
                       'SHAPEOPS_REPORT_DIR': str(directory / 'training-reports'),
                       'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
        process = subprocess.Popen([sys.executable, '-m', 'backend.evaluate_dataset', str(manifest.resolve()),
                                    '--output', str(report), '--worker'],
                                   cwd=Path(__file__).resolve().parents[1], env=environment,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            _stop(process)
            raise
        if code != 0:
            raise RuntimeError('Evaluation failed within supported corpus and resource limits')
        payload = read_regular(report, MAX_REPORT_BYTES)
        value = json.loads(payload)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Publish a complete report atomically without replacing earlier evidence.
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
        return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.manifest, args.output)
    else:
        report = run_evaluation(args.manifest, args.output, args.timeout)
        print(json.dumps({'dataset': report['dataset'], 'manifest_sha256': report['manifest_sha256'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
