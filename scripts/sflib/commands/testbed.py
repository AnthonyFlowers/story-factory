from __future__ import annotations

import json
import os
import shutil
import subprocess

from .. import SFError, config


def run(args):
    src = os.path.join(config.root(), "testbed", "team-repo")
    dest = os.path.abspath(args.path)
    if not os.path.isdir(src):
        raise SFError("testbed/team-repo is missing", 1)
    if os.path.exists(dest) and os.listdir(dest):
        raise SFError("%s exists and is not empty" % dest, 1)
    shutil.copytree(src, dest, dirs_exist_ok=True)
    git = ["git", "-c", "user.name=testbed", "-c", "user.email=testbed@example.invalid"]
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(git + ["commit", "-q", "-m", "testbed: initial commit"], cwd=dest, check=True)
    snippet = {
        "jira": {"skill": "pull-jira-ticket-stub", "project_key": "DEMO"},
        "repos": [{"name": "accounts-api", "path": dest, "openapi": ["openapi.json"],
                   "docs": ["docs"], "notes": "LoopBack 4 service (testbed)"}],
    }
    print("created %s" % dest)
    print("merge this into factory.config.json (keep the other keys from the example):")
    print(json.dumps(snippet, indent=2))
    return 0


def register(subparsers):
    p = subparsers.add_parser("testbed", help="create the dummy team repo from testbed/team-repo at PATH")
    p.add_argument("path")
    p.set_defaults(func=run)
