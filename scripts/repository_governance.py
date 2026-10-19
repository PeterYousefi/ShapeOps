"""Read-only verification of ShapeOps public repository and main protections."""
import argparse
from datetime import datetime, timezone
import json
import subprocess

REQUIRED_CHECKS = {"application", "container", "kubernetes", "terraform"}


def policy_violations(repository, protection):
    failures = []
    if repository.get("visibility") != "public":
        failures.append("Repository must remain public.")
    if repository.get("default_branch") != "main":
        failures.append("Expected default branch main.")
    if protection.get("enforce_admins", {}).get("enabled") is not True:
        failures.append("Administrators must be subject to branch protection.")
    if protection.get("allow_force_pushes", {}).get("enabled") is not False:
        failures.append("Force pushes must be explicitly prohibited.")
    if protection.get("allow_deletions", {}).get("enabled") is not False:
        failures.append("Main branch deletion must be explicitly prohibited.")
    if protection.get("required_pull_request_reviews") is None:
        failures.append("Pull requests must be required before merging.")
    if protection.get("required_conversation_resolution", {}).get("enabled") is not True:
        failures.append("Review conversations must be resolved.")
    checks = protection.get("required_status_checks") or {}
    if checks.get("strict") is not True:
        failures.append("Status checks must require an up-to-date branch.")
    missing = REQUIRED_CHECKS - set(checks.get("contexts", []))
    if missing:
        failures.append("Missing required checks: " + ", ".join(sorted(missing)))
    return failures


def github(path):
    response = subprocess.run(
        ["gh", "api", path], check=True, capture_output=True, text=True, timeout=30
    )
    return json.loads(response.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="PeterYousefi/ShapeOps")
    args = parser.parse_args()
    try:
        repository = github(f"repos/{args.repository}")
        protection = github(f"repos/{args.repository}/branches/main/protection")
    except (subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise SystemExit("Unable to verify GitHub governance; check gh authentication and network access.") from error
    failures = policy_violations(repository, protection)
    print(json.dumps({
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "repository": args.repository,
        "visibility": repository.get("visibility"),
        "default_branch": repository.get("default_branch"),
        "required_checks": (protection.get("required_status_checks") or {}).get("contexts", []),
        "verified": not failures,
        "violations": failures,
    }, indent=2))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
