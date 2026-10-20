from copy import deepcopy
import pytest
from scripts.validate_iac_report import validate_report


def report():
    return {"Results": [{"Class": "config", "Type": "terraform", "MisconfSummary": {"Successes": 10, "Failures": 0}}]}


def test_real_gate_rejects_findings_and_positive_control_requires_them():
    clean = report()
    assert validate_report(clean)["terraform_checks"] == 10
    with pytest.raises(ValueError, match="Positive control"):
        validate_report(clean, positive_control=True)
    bad = deepcopy(clean)
    bad["Results"][0]["Misconfigurations"] = [{"ID": "AZU-0012", "Severity": "CRITICAL"}]
    with pytest.raises(ValueError, match="AZU-0012"):
        validate_report(bad)
    assert validate_report(bad, positive_control=True)["high_critical_findings"] == 1


@pytest.mark.parametrize("broken", [{}, {"Results": []}, {"Results": [{"Type": "dockerfile"}]},
    {"Results": [{"Class": "config", "Type": "terraform", "MisconfSummary": {"Successes": 0, "Failures": 0}}]},
    {"Results": [{"Class": "config", "Type": "terraform"}]}])
def test_missing_or_skipped_checks_fail_closed(broken):
    with pytest.raises(ValueError):
        validate_report(broken)


def test_metadata_only_entries_do_not_hide_executed_root_checks():
    scanned = report()
    scanned["Results"].append({"Class": "config", "Type": "terraform", "Target": "main.tf"})
    assert validate_report(scanned)["terraform_checks"] == 10
