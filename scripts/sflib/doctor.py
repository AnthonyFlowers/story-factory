from __future__ import annotations

import os
import subprocess
import sys

REQUIRED_IGNORES = [
    "factory/jobs/*", "!factory/jobs/.gitkeep", "factory/backlog.md", "factory.config.json",
    "templates/local/*", "!templates/local/.gitkeep", ".claude/settings.local.json", "__pycache__/",
]
GUARDED = ["factory/jobs", "factory/backlog.md", "factory.config.json", "templates/local",
           ".claude/settings.local.json"]
ALLOWED_TRACKED = {"factory/jobs/.gitkeep", "templates/local/.gitkeep"}


def check(root: str) -> list:
    """Return a list of problem strings (empty means OK)."""
    problems = []
    gi = os.path.join(root, ".gitignore")
    lines = set()
    if os.path.isfile(gi):
        with open(gi) as f:
            lines = {l.strip() for l in f}
    else:
        problems.append(".gitignore is missing")
    for need in REQUIRED_IGNORES:
        if gi and os.path.isfile(gi) and need not in lines:
            problems.append(".gitignore is missing the line %r" % need)
    try:
        out = subprocess.run(["git", "ls-files"] + GUARDED, cwd=root, capture_output=True,
                             text=True, check=True).stdout
        for path in out.split("\n"):
            if path and path not in ALLOWED_TRACKED:
                problems.append("tracked file that must stay local: %s" % path)
    except (OSError, subprocess.CalledProcessError) as e:
        problems.append("git ls-files failed: %s" % e)
    if sys.version_info < (3, 9):
        problems.append("python3 is %d.%d, need 3.9 or newer" % sys.version_info[:2])
    return problems
