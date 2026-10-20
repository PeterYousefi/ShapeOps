"""Fail closed on mutable remote Actions and unnecessary token write scopes."""
from pathlib import Path
import re
import yaml


PIN = re.compile(r"[^\s@]+/[^\s@]+@[0-9a-f]{40}\Z")


def violations(workflow: dict) -> list[str]:
    errors = []
    events = workflow.get("on", workflow.get(True, {}))
    if "pull_request_target" in events:
        errors.append("pull_request_target is forbidden")
    if workflow.get("permissions") != {"contents": "read"}:
        errors.append("workflow token must be contents: read only")
    for name, job in workflow.get("jobs", {}).items():
        if "permissions" in job and job["permissions"] not in ({}, {"contents": "read"}):
            errors.append(f"{name}: token permission override is forbidden")
        entries = [job] if "uses" in job else job.get("steps", [])
        for entry in entries:
            reference = entry.get("uses")
            if reference is None:
                continue
            if not isinstance(reference, str) or (not reference.startswith("./") and not PIN.fullmatch(reference)):
                errors.append(f"{name}: action requires full commit SHA: {reference}")
            if isinstance(reference, str) and reference.startswith("actions/checkout@"):
                if entry.get("with", {}).get("persist-credentials") is not False:
                    errors.append(f"{name}: checkout must not persist credentials")
    return errors


def main() -> int:
    errors = []
    for path in sorted(Path(".github/workflows").glob("*.y*ml")):
        errors.extend(f"{path}: {error}" for error in violations(yaml.safe_load(path.read_text())))
    for error in errors:
        print(error)
    if not errors:
        print("Workflow action pins and token permissions verified")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
