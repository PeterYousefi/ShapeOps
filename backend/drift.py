"""Actual per-request geometry comparison, not calibrated industrial drift inference."""
import hashlib
import json
import time
from typing import get_args
import numpy as np
from backend.contracts import Surface
from backend.responses import DriftObservation, InferenceResult

LABELS = get_args(Surface)
FEATURES = ['Face count', 'Edge count', 'Smallest extent', 'Middle extent', 'Largest extent',
            'Aspect ratio', 'Edges per face', 'Total face area', *[f'{label} face fraction' for label in LABELS]]


def vector(geometry: dict) -> list[float]:
    faces = geometry['faces']
    if not faces or geometry['face_count'] != len(faces):
        raise ValueError('Geometry face count is invalid')
    extents = sorted(geometry['bounds'])
    return [float(geometry['face_count']), float(geometry['edge_count']), *map(float, extents),
            float(extents[-1] / max(extents[0], 1e-6)), float(geometry['edge_count'] / len(faces)),
            float(sum(face['area'] for face in faces)),
            *[sum(face['surface'] == label for face in faces) / len(faces) for label in LABELS]]


def observation(result: InferenceResult, samples: dict[str, dict]) -> DriftObservation:
    reference = [vector(samples[key]) for key in sorted(samples)]
    matrix = np.asarray(reference, dtype=float)
    if matrix.ndim != 2 or not len(matrix) or not np.isfinite(matrix).all() or (matrix < 0).any():
        raise ValueError('Invalid geometry reference')
    mean = matrix.mean(axis=0)
    # A five-percent relative floor avoids undefined zero-variance comparisons.
    scale = np.maximum(matrix.std(axis=0), np.maximum(abs(mean) * .05, 1e-6))
    current = {'face_count': result.face_count, 'edge_count': result.edge_count, 'bounds': result.bounds,
               'faces': [{'area': face.area, 'surface': face.surface} for face in result.faces]}
    values = np.asarray(vector(current), dtype=float)
    deviations = abs(values - mean) / scale
    reference_id = hashlib.sha256(json.dumps({'features': FEATURES, 'reference': reference, 'method': 'absolute-standardized-deviation-v1', 'relative_floor': .05, 'absolute_floor': 1e-6, 'threshold': 3.0}, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return DriftObservation.model_validate({
        'id': result.trace_id, 'at': time.time(), 'source': result.source, 'model': result.model,
        'reference_id': reference_id, 'reference_scope': 'Owned procedural sample geometries; screening only',
        'reference_parts': len(reference), 'threshold': 3.0, 'warning': bool((deviations >= 3).any()),
        'ood_score': result.ood_score, 'ood': result.ood,
        'features': [{'name': name, 'value': float(value), 'reference_mean': float(center),
                      'reference_scale': float(width), 'deviation': float(deviation)}
                     for name, value, center, width, deviation in zip(FEATURES, values, mean, scale, deviations)]})
