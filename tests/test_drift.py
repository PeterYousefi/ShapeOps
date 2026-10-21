"""Explicit geometry-screening fixtures, never industrial drift validation."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from backend.drift import observation, vector
from backend.responses import DriftObservation


def fixture():
    geometry = {'face_count': 1, 'edge_count': 3, 'bounds': [1.0, 2.0, 3.0],
                'faces': [{'area': 2.0, 'surface': 'Planar'}]}
    result = SimpleNamespace(face_count=1, edge_count=3, bounds=[1.0, 2.0, 3.0],
                             faces=[SimpleNamespace(area=2.0, surface='Planar')], trace_id='a' * 32,
                             source='sample', model='explicit-unit-fixture', ood_score=-.1, ood=False)
    return geometry, result


def test_reference_match_shift_and_identity_are_derived_from_actual_values():
    geometry, result = fixture()
    baseline = observation(result, {'owned-fixture': geometry})
    assert not baseline.warning and all(feature.deviation == 0 for feature in baseline.features)
    assert all(feature.reference_scale > 0 for feature in baseline.features)
    result.bounds = [1.0, 2.0, 300.0]
    shifted = observation(result, {'owned-fixture': geometry})
    assert shifted.warning and shifted.reference_id == baseline.reference_id
    assert next(feature for feature in shifted.features if feature.name == 'Largest extent').value == 300
    changed = deepcopy(geometry)
    changed['edge_count'] = 10
    assert observation(result, {'owned-fixture': changed}).reference_id != baseline.reference_id
    assert sum(vector(geometry)[8:]) == 1


@pytest.mark.parametrize('change', ['summary', 'deviation', 'duplicate', 'nonfinite', 'ood'])
def test_saved_drift_contract_rejects_inconsistent_evidence(change):
    geometry, result = fixture()
    payload = observation(result, {'fixture': geometry}).model_dump()
    if change == 'summary':
        payload['warning'] = True
    elif change == 'deviation':
        payload['features'][0]['deviation'] = 10
    elif change == 'duplicate':
        payload['features'][1]['name'] = payload['features'][0]['name']
    elif change == 'nonfinite':
        payload['features'][0]['value'] = float('nan')
    else:
        payload['ood'] = True
    with pytest.raises(ValidationError):
        DriftObservation.model_validate(payload)
