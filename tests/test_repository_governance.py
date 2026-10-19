from copy import deepcopy
import pytest
from scripts.repository_governance import policy_violations

REPOSITORY = {"visibility": "public", "default_branch": "main"}
PROTECTION = {
    "enforce_admins": {"enabled": True},
    "allow_force_pushes": {"enabled": False},
    "allow_deletions": {"enabled": False},
    "required_pull_request_reviews": {"required_approving_review_count": 0},
    "required_conversation_resolution": {"enabled": True},
    "required_status_checks": {
        "strict": True,
        "contexts": ["application", "container", "kubernetes", "terraform"],
    },
}


def test_expected_governance_is_accepted():
    assert not policy_violations(REPOSITORY, PROTECTION)


@pytest.mark.parametrize("field", [
    "enforce_admins", "allow_force_pushes", "allow_deletions",
    "required_pull_request_reviews", "required_conversation_resolution",
    "required_status_checks",
])
def test_missing_protection_fails_closed(field):
    protection = deepcopy(PROTECTION)
    protection.pop(field)
    assert policy_violations(REPOSITORY, protection)


@pytest.mark.parametrize("field,value", [
    ("allow_force_pushes", True), ("allow_deletions", True),
    ("enforce_admins", False), ("required_conversation_resolution", False),
])
def test_weakened_protection_is_detected(field, value):
    protection = deepcopy(PROTECTION)
    protection[field]["enabled"] = value
    assert policy_violations(REPOSITORY, protection)


def test_missing_or_stale_checks_are_rejected():
    protection = deepcopy(PROTECTION)
    protection["required_status_checks"]["contexts"].remove("container")
    protection["required_status_checks"]["strict"] = False
    failures = policy_violations(REPOSITORY, protection)
    assert any("container" in failure for failure in failures)
    assert any("up-to-date" in failure for failure in failures)


def test_private_or_wrong_default_branch_is_detected():
    assert policy_violations({"visibility": "private", "default_branch": "develop"}, PROTECTION)
