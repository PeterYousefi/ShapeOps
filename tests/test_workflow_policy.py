from copy import deepcopy
from pathlib import Path
import pytest
import yaml
from scripts.workflow_policy import violations


@pytest.fixture
def workflow():
    return yaml.safe_load(Path('.github/workflows/quality.yml').read_text())


def test_all_current_workflows_are_pinned_and_least_privilege():
    quality = yaml.safe_load(Path(".github/workflows/quality.yml").read_text())
    assert {"application", "container", "kubernetes", "terraform"} <= set(quality["jobs"])
    for path in Path('.github/workflows').glob('*.y*ml'):
        assert violations(yaml.safe_load(path.read_text())) == [], path
    config = yaml.safe_load(Path('.github/dependabot.yml').read_text())
    assert any(update['package-ecosystem'] == 'github-actions' for update in config['updates'])


@pytest.mark.parametrize('reference', ['actions/checkout@v4', 'actions/checkout@main', 'actions/checkout@1234567', 'docker://image:latest'])
def test_mutable_or_short_action_refs_fail(workflow, reference):
    workflow['jobs']['application']['steps'][0]['uses'] = reference
    assert any('full commit SHA' in error for error in violations(workflow))


def test_write_scopes_dangerous_trigger_and_persisted_credentials_fail(workflow):
    cases = []
    changed = deepcopy(workflow)
    changed['permissions']['contents'] = 'write'
    cases.append(changed)
    changed = deepcopy(workflow)
    changed['jobs']['application']['permissions'] = {'id-token': 'write'}
    cases.append(changed)
    changed = deepcopy(workflow)
    changed['on'] = {'pull_request_target': {}}
    cases.append(changed)
    changed = deepcopy(workflow)
    changed['jobs']['application']['steps'][0]['with']['persist-credentials'] = True
    cases.append(changed)
    assert all(violations(case) for case in cases)


def test_reusable_workflow_refs_are_checked(workflow):
    workflow['jobs']['external'] = {'uses': 'example/workflows/.github/workflows/check.yml@main'}
    assert any('full commit SHA' in error for error in violations(workflow))
