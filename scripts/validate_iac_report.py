"""Reject empty/skipped Terraform scans and enforce the high/critical gate."""
import argparse
import json
from pathlib import Path


def validate_report(report: dict, *, positive_control: bool = False) -> dict:
    results = report.get("Results")
    if not isinstance(results, list):
        raise ValueError("Missing scan results")
    terraform = [r for r in results if isinstance(r, dict) and r.get("Type") == "terraform" and r.get("Class") == "config"]
    checked = 0
    findings = []
    for result in terraform:
        summary = result.get("MisconfSummary")
        if summary is not None:
            for key in ("Successes", "Failures"):
                value = summary.get(key)
                if type(value) is not int or value < 0:
                    raise ValueError("Missing Terraform check coverage")
                checked += value
        for finding in result.get("Misconfigurations", []) or []:
            severity = finding.get("Severity")
            if severity not in {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                raise ValueError("Unknown finding severity")
            if severity in {"HIGH", "CRITICAL"}:
                if not finding.get("ID"):
                    raise ValueError("Finding has no rule identity")
                findings.append(finding["ID"])
    if not terraform or not checked:
        raise ValueError("No Terraform checks executed")
    if positive_control and not findings:
        raise ValueError("Positive control did not detect insecure configuration")
    if not positive_control and findings:
        raise ValueError(f"High/critical Terraform findings: {', '.join(findings)}")
    return {"terraform_checks": checked, "high_critical_findings": len(findings), "positive_control": positive_control}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--positive-control", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(validate_report(json.loads(arguments.report.read_text()), positive_control=arguments.positive_control)))


if __name__ == "__main__":
    main()
