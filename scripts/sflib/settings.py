from __future__ import annotations

import json
import os

from . import config, jobs


def build(cfg: dict) -> dict:
    dirs = [r["path"] for r in cfg.get("repos", [])] + [t["path"] for t in cfg.get("team_docs", [])]
    deny = ["Edit(//%s/**)" % d.lstrip("/") for d in dirs]
    deny += ["Read(//%s/**)" % d.lstrip("/") for d in cfg.get("deny_read", [])]
    return {"permissions": {"additionalDirectories": dirs, "deny": deny}}


def write(cfg: dict) -> str:
    path = os.path.join(config.root(), ".claude", "settings.local.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    jobs.atomic_write(path, json.dumps(build(cfg), indent=2) + "\n")
    return path
