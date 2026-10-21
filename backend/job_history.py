"""Bounded read-only discovery of trusted local candidate job metadata."""
import heapq
import os
from pathlib import Path
import re
import stat
from backend.responses import CandidateJob

MAX_JOB_BYTES = 64 * 1024
MAX_DISCOVERED_JOBS = 1000
IDENTITY = re.compile(r'[a-f0-9]{32}\Z')


class HistoryCapacityError(ValueError):
    pass


def get_job(root: Path, identity: str) -> CandidateJob | None:
    if not IDENTITY.fullmatch(identity):
        return None
    directory = root / identity
    if root.is_symlink() or directory.is_symlink():
        raise ValueError('Candidate job directory must not be a symlink')
    path = directory / 'job.json'
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('Candidate job metadata must be a regular file')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            payload = stream.read(MAX_JOB_BYTES + 1)
        if len(payload) > MAX_JOB_BYTES:
            raise ValueError('Candidate job metadata exceeds read budget')
    finally:
        os.close(descriptor)
    job = CandidateJob.model_validate_json(payload)
    if job.id != identity:
        raise ValueError('Candidate job identity does not match its directory')
    return job


def list_jobs(root: Path, limit: int = 20) -> list[CandidateJob]:
    if not 1 <= limit <= 100:
        raise ValueError('Candidate history limit must be between one and one hundred')
    if root.is_symlink():
        raise ValueError('Candidate job root must not be a symlink')
    if not root.exists():
        return []
    newest: list[tuple[float, str, CandidateJob]] = []
    discovered = 0
    with os.scandir(root) as entries:
        for entry in entries:
            discovered += 1
            # Count even unrelated entries to bound enumeration under corruption.
            if discovered > MAX_DISCOVERED_JOBS:
                raise HistoryCapacityError('Candidate job history requires archival before discovery')
            if not IDENTITY.fullmatch(entry.name):
                continue
            job = get_job(root, entry.name)
            if job is None:
                continue  # Reservation may precede the first atomic job write.
            heapq.heappush(newest, (job.started_at, job.id, job))
            if len(newest) > limit:
                heapq.heappop(newest)
    return [item[2] for item in sorted(newest, reverse=True)]
