"""Per-job claims: <job>/.claim is created atomically (O_CREAT|O_EXCL) so only one
session drives a job at a time. job.json `claimed_by` mirrors the holder."""
from __future__ import annotations

import json
import os
import socket

from . import jobs

CLAIM = ".claim"


def default_who() -> str:
    return "%s:%d" % (socket.gethostname(), os.getppid())


def read_claim(job_id: str):
    try:
        with open(os.path.join(jobs.job_dir(job_id), CLAIM)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def claim(job_id: str, who=None, force=False):
    """Return (True, info) when claimed, (False, existing_info) when busy."""
    who = who or default_who()
    path = os.path.join(jobs.job_dir(job_id), CLAIM)
    info = {"who": who, "pid": os.getpid(), "time": jobs.now()}
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if force and os.path.exists(path):
        os.unlink(path)
    try:
        fd = os.open(path, flags, 0o644)
    except FileExistsError:
        existing = read_claim(job_id) or {"who": "unknown", "time": "unknown"}
        return False, existing
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(info) + "\n")
    jobs.update_job(job_id, sets=["claimed_by=" + json.dumps(who)])
    return True, info


def release(job_id: str) -> None:
    try:
        os.unlink(os.path.join(jobs.job_dir(job_id), CLAIM))
    except FileNotFoundError:
        pass
    jobs.update_job(job_id, sets=["claimed_by=null"])
