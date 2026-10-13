from __future__ import annotations

import json
import os

from . import config, jobs


def build(cfg: dict) -> dict:
    dirs = [r["path"] for r in cfg.get("repos", [])] + [t["path"] for t in cfg.get("team_docs", [])]
    deny = ["Edit(//%s/**)" % d.lstrip("/") for d in dirs]
    deny += ["Read(//%s/**)" % d.lstrip("/") for d in cfg.get("deny_read", [])]
    # Allow rules live here, not only in the shared .claude/settings.json: Claude Code ignores
    # that file's allow rules until the folder is trusted, but honours settings.local.json.
    allow = ["Bash(python3 scripts/sf.py *)", "Bash(python3 scripts/jira_stub.py *)"]
    skill = (cfg.get("jira") or {}).get("skill")
    if skill:
        allow.append("Skill(%s)" % skill)
    return {"permissions": {"allow": allow, "additionalDirectories": dirs, "deny": deny}}


def write(cfg: dict) -> str:
    path = os.path.join(config.root(), ".claude", "settings.local.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    jobs.atomic_write(path, json.dumps(build(cfg), indent=2) + "\n")
    return path
