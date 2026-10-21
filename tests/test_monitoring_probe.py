"""Synthetic protocol payloads test fail-closed probe behavior, not runtime telemetry."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts.monitoring_probe import vector_value, validate_dashboard


def vector(value='2'):
    return {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'job': 'shapeops'}, 'value': [1, value]}]}}


def test_metric_probe_requires_one_finite_successful_series():
    assert vector_value(vector()) == 2
    for value in ('NaN', '+Inf', '-Inf', 'not-a-number'):
        with pytest.raises(ValueError):
            vector_value(vector(value))
    for payload in ({**vector(), 'status': 'error'}, {**vector(), 'warnings': ['partial query']},
                    {'status': 'success', 'data': {'resultType': 'vector', 'result': []}},
                    {'status': 'success', 'data': {'resultType': 'matrix', 'result': vector()['data']['result']}}):
        with pytest.raises(ValueError):
            vector_value(payload)
    duplicate = vector()
    duplicate['data']['result'] *= 2
    with pytest.raises(ValueError):
        vector_value(duplicate)


def test_dashboard_probe_requires_complete_provisioned_panel_coverage():
    spec = json.loads(Path('monitoring/dashboard.json').read_text())
    payload = {'dashboard': deepcopy(spec), 'meta': {'provisioned': True}}
    assert len(validate_dashboard(payload, spec)) == 3
    for mutate in (
        lambda p: p['meta'].update(provisioned=False),
        lambda p: p['dashboard'].update(uid='unrelated'),
        lambda p: p['dashboard']['panels'].pop(),
        lambda p: p['dashboard']['panels'][0]['datasource'].update(uid='missing'),
        lambda p: p['dashboard']['panels'][0]['targets'][0].update(expr='vector(1)'),
    ):
        invalid = deepcopy(payload)
        mutate(invalid)
        with pytest.raises(ValueError):
            validate_dashboard(invalid, spec)
