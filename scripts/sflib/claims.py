"""Per-job claims: <job>/.claim is created atomically (O_CREAT|O_EXCL) so only one
session drives a job at a time. job.json `claimed_by` mirrors the holder."""
from __future__ import annotations

import fcntl
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


def holder_is_dead(who) -> bool:
    """True when `who` is the default `<this hostname>:<pid>` label and that pid is gone.
    Custom --who labels, other hosts and unreadable labels are never reported dead."""
    host, sep, pid = str(who).rpartition(":")
    if not sep or host != socket.gethostname() or not pid.isdigit() or int(pid) <= 1:
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False  # EPERM: the process exists
    return False


def claim(job_id: str, who=None, force=False):
    """Return (True, info) when claimed, (False, existing_info) when busy. A claim whose
    holder process is dead (same host) is taken over; info then has `took_over` set."""
    who = who or default_who()
    jd = jobs.job_dir(job_id)
    path = os.path.join(jd, CLAIM)
    info = {"who": who, "pid": os.getpid(), "time": jobs.now()}
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    dfd = os.open(jd, os.O_RDONLY)  # lock the job directory so takeover cannot race
    try:
        fcntl.flock(dfd, fcntl.LOCK_EX)
        existing = read_claim(job_id) if os.path.exists(path) else None
        if existing is not None and not force and holder_is_dead(existing.get("who")):
            info["took_over"] = existing.get("who")
            force = True
        if force and os.path.exists(path):
            os.unlink(path)
        try:
            fd = os.open(path, flags, 0o644)
        except FileExistsError:
            return False, read_claim(job_id) or {"who": "unknown", "time": "unknown"}
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(info) + "\n")
        jobs.update_job(job_id, sets=["claimed_by=" + json.dumps(who)])
        return True, info
    finally:
        os.close(dfd)


def release(job_id: str) -> None:
    try:
        os.unlink(os.path.join(jobs.job_dir(job_id), CLAIM))
    except FileNotFoundError:
        pass
    jobs.update_job(job_id, sets=["claimed_by=null"])
