"""Pure gate checks are test evidence, not authorization or production promotion."""
from copy import deepcopy
import pytest
from backend.governance import evaluate_gates, eligible


@pytest.mark.parametrize('metric', [True, False, '0.99', None, float('nan'), float('inf'), -0.01, 1.01, 10 ** 1000])
def test_invalid_quality_evidence_is_rejected(metric):
    with pytest.raises(ValueError, match='finite probability'):
        evaluate_gates(metric, True, True, True)


@pytest.mark.parametrize('flag', ['false', 'true', 0, 1, None, [], {}])
@pytest.mark.parametrize('position', [0, 1, 2])
def test_release_flags_are_never_coerced(flag, position):
    flags = [True, True, True]
    flags[position] = flag
    with pytest.raises(ValueError, match='explicit booleans'):
        evaluate_gates(.95, *flags)


@pytest.mark.parametrize('authorization', ['false', 'true', 1, 0, None, [], {}, object()])
def test_truthy_authorization_values_never_authorize(authorization):
    assert eligible(evaluate_gates(.95, True, True, True), authorization) is False


def test_gate_decisions_require_exact_complete_boolean_evidence():
    good = evaluate_gates(.95, True, True, True)
    assert eligible(good) is False
    assert eligible(good, True) is True
    for field in good:
        for bad_value in ('false', 'true', 1, 0, None, [], {}, False):
            bad = {**good, field: bad_value}
            assert eligible(bad, True) is False
        missing = deepcopy(good)
        missing.pop(field)
        assert eligible(missing, True) is False
    assert eligible({**good, 'extra': True}, True) is False
    for invalid in (None, [], 'approved', True):
        assert eligible(invalid, True) is False
    assert good == evaluate_gates(.95, True, True, True)


def test_quality_boundary_and_real_negative_gates_are_preserved():
    assert not evaluate_gates(.849999, True, True, True)['quality']
    assert evaluate_gates(.85, True, True, True)['quality']
    for metric in (0, 1):
        assert type(evaluate_gates(metric, True, True, True)['quality']) is bool
    for flags in ((False, True, True), (True, False, True), (True, True, False)):
        assert eligible(evaluate_gates(.95, *flags), True) is False
