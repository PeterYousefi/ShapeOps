"""Fail closed unless real captured Kind states demonstrate revision rollback."""
import hashlib
import json
from pathlib import Path
import sys

FAULT_PATH = '/proc/shapeops-rollback-fault'


def container(document):
    containers = document['spec']['template']['spec']['containers'] if document.get('kind') == 'Deployment' else document['spec']['containers']
    return next(item for item in containers if item['name'] == 'shapeops')


def faulted(document):
    return any(item.get('name') == 'SHAPEOPS_DATA_DIR' and item.get('value') == FAULT_PATH for item in container(document).get('env', []))


def verify(before: dict, failed: dict, restored: dict, pods: dict) -> dict:
    if not before['metadata'].get('uid') or len({item['metadata']['uid'] for item in (before, failed, restored)}) != 1:
        raise ValueError('Rollback snapshots must identify the same deployment')
    generations = [item['metadata']['generation'] for item in (before, failed, restored)]
    if not generations[0] < generations[1] < generations[2]:
        raise ValueError('Expected observed successive deployment generations')
    revisions = [int(item['metadata']['annotations']['deployment.kubernetes.io/revision']) for item in (before, failed, restored)]
    if not 0 < revisions[0] < revisions[1] < revisions[2]:
        raise ValueError('Expected three ordered deployment revisions')
    for item in (before, failed, restored):
        if item['status'].get('observedGeneration', 0) < item['metadata']['generation']:
            raise ValueError('Controller has not observed captured generation')
    if before['status'].get('availableReplicas', 0) < 1 or restored['status'].get('availableReplicas', 0) < 1:
        raise ValueError('Baseline and restored revision must be available')
    if failed['status'].get('availableReplicas', 0) != 0 or not faulted(failed) or faulted(before) or faulted(restored):
        raise ValueError('Expected an unavailable isolated fault revision only')
    if before['spec']['template']['spec'] != restored['spec']['template']['spec']:
        raise ValueError('Rollback did not restore exact original pod specification')
    crashed = False
    for pod in pods['items']:
        if not faulted(pod):
            continue
        for status in pod.get('status', {}).get('containerStatuses', []):
            if status['name'] == 'shapeops' and (status.get('restartCount', 0) > 0 or status.get('state', {}).get('terminated', {}).get('exitCode', 0) != 0):
                crashed = True
    if not crashed:
        raise ValueError('No actual failed candidate-container execution observed')
    return {'scope': 'Disposable Kind revision rollback only; no production mutation.',
            'baseline_revision': revisions[0], 'failed_revision': revisions[1], 'restored_revision': revisions[2],
            'restored_pod_spec_sha256': hashlib.sha256(json.dumps(restored['spec']['template']['spec'], sort_keys=True).encode()).hexdigest(),
            'failed_execution_observed': crashed, 'restored_available_replicas': restored['status']['availableReplicas']}


def main():
    root = Path(sys.argv[1])
    before, failed, restored, pods = [json.loads((root / name).read_text()) for name in ('baseline.json', 'failed.json', 'restored.json', 'failed-pods.json')]
    report = verify(before, failed, restored, pods)
    (root / 'rollback-evidence.json').write_text(json.dumps(report, indent=2))
    print('Isolated failed revision and exact restored deployment state verified')


if __name__ == '__main__':
    main()
