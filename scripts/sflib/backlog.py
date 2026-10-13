"""The backlog file: claim the first unchecked item, mark it done with a job id."""
from __future__ import annotations

import fcntl
import os
import shutil
import sys

from . import SFError, config

PREFIXES = ("bug", "spike", "epic", "refine")
OPEN = "- [ ] "
CLAIMED = " → claimed"


def backlog_path() -> str:
    return os.environ.get("STORY_FACTORY_BACKLOG") or os.path.join(config.root(), "factory", "backlog.md")


def parse_item(text: str):
    """Return (type, text without prefix). Bare lines are stories; refine keeps type 'refine'."""
    t = text.strip()
    head, sep, rest = t.partition(":")
    if sep and head.strip().lower() in PREFIXES and rest.strip():
        return head.strip().lower(), rest.strip()
    return "story", t


def _ensure(path: str) -> None:
    if os.path.exists(path):
        return
    example = os.path.join(config.root(), "factory", "backlog.example.md")
    if not os.path.isfile(example):
        raise SFError("no backlog at %s and no example to copy" % path)
    shutil.copyfile(example, path)
    print("note: %s was missing, copied from backlog.example.md" % path, file=sys.stderr)


def claim():
    """Return (line_no, type, text) of the first unchecked item, or None. Locked with flock."""
    path = backlog_path()
    _ensure(path)
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            lines = f.read().split("\n")
            for i, line in enumerate(lines):
                if line.startswith(OPEN):
                    raw = line[len(OPEN):].rstrip()
                    lines[i] = "- [x] " + raw + CLAIMED
                    f.seek(0)
                    f.truncate()
                    f.write("\n".join(lines))
                    f.flush()
                    typ, text = parse_item(raw)
                    return i + 1, typ, text
            return None
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def done(line_no: int, job_id: str) -> None:
    path = backlog_path()
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            lines = f.read().split("\n")
            if not 1 <= line_no <= len(lines) or not lines[line_no - 1].endswith(CLAIMED):
                raise SFError("line %d is not a claimed backlog item" % line_no)
            lines[line_no - 1] = lines[line_no - 1][: -len(CLAIMED)] + " → " + job_id
            f.seek(0)
            f.truncate()
            f.write("\n".join(lines))
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
