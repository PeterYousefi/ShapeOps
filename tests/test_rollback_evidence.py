"""Synthetic snapshots test evidence rejection; actual rollback is hosted Kind only."""
from copy import deepcopy
import pytest
from scripts.rollback_evidence import FAULT_PATH, verify


def snapshots():
    base = {'kind': 'Deployment', 'metadata': {'uid': 'owned-unit-deployment', 'generation': 1, 'annotations': {'deployment.kubernetes.io/revision': '1'}},
            'spec': {'template': {'spec': {'containers': [{'name': 'shapeops', 'image': 'owned-fixture:local'}]}}},
            'status': {'observedGeneration': 1, 'availableReplicas': 1}}
    failed = deepcopy(base)
    failed['metadata']['generation'] = 2
    failed['status']['observedGeneration'] = 2
    failed['metadata']['annotations']['deployment.kubernetes.io/revision'] = '2'
    failed['spec']['template']['spec']['containers'][0]['env'] = [{'name': 'SHAPEOPS_DATA_DIR', 'value': FAULT_PATH}]
    failed['status']['availableReplicas'] = 0
    restored = deepcopy(base)
    restored['metadata']['generation'] = 3
    restored['status']['observedGeneration'] = 3
    restored['metadata']['annotations']['deployment.kubernetes.io/revision'] = '3'
    pods = {'items': [{'spec': deepcopy(failed['spec']['template']['spec']),
                       'status': {'containerStatuses': [{'name': 'shapeops', 'restartCount': 1}]}}]}
    return base, failed, restored, pods


def test_complete_rollback_evidence_preserves_exact_revision_identity():
    report = verify(*snapshots())
    assert report['baseline_revision'] == 1 and report['restored_revision'] == 3
    assert len(report['restored_pod_spec_sha256']) == 64


@pytest.mark.parametrize('case', ['healthy_fault', 'no_crash', 'different_image', 'no_new_revision', 'unobserved', 'no_recovery', 'wrong_deployment'])
def test_incomplete_or_false_rollback_evidence_fails_closed(case):
    before, failed, restored, pods = snapshots()
    if case == 'healthy_fault':
        failed['status']['availableReplicas'] = 1
    elif case == 'no_crash':
        pods['items'][0]['status']['containerStatuses'][0]['restartCount'] = 0
    elif case == 'different_image':
        restored['spec']['template']['spec']['containers'][0]['image'] = 'other:fixture'
    elif case == 'no_new_revision':
        restored['metadata']['annotations']['deployment.kubernetes.io/revision'] = '2'
    elif case == 'unobserved':
        failed['status']['observedGeneration'] = 0
    elif case == 'wrong_deployment':
        restored['metadata']['uid'] = 'unrelated-unit-deployment'
    else:
        restored['status']['availableReplicas'] = 0
    with pytest.raises(ValueError):
        verify(before, failed, restored, pods)
