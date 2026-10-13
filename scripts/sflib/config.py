from __future__ import annotations

import json
import os

from . import SFError

DEFAULT_ALWAYS_HUMAN = ["pii", "auth", "payments", "regulatory"]


def root() -> str:
    """Repo root, found from the location of scripts/sf.py (this file is scripts/sflib/config.py)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def jobs_dir() -> str:
    return os.environ.get("STORY_FACTORY_JOBS") or os.path.join(root(), "factory", "jobs")


def config_path() -> str:
    return os.environ.get("STORY_FACTORY_CONFIG") or os.path.join(root(), "factory.config.json")


def _abs(path: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(root(), path)
    return os.path.normpath(path)


def _resolve(cfg: dict) -> dict:
    for key in ("repos", "team_docs"):
        for entry in cfg.get(key, []):
            if "path" in entry:
                entry["path"] = _abs(entry["path"])
    cfg["deny_read"] = [_abs(p) for p in cfg.get("deny_read", [])]
    esc = cfg.setdefault("escalation", {})
    esc.setdefault("always_human", list(DEFAULT_ALWAYS_HUMAN))
    esc.setdefault("extra_terms", [])
    cfg.setdefault("repos", [])
    cfg.setdefault("team_docs", [])
    cfg.setdefault("template", "default")
    return cfg


def try_load():
    """Return the resolved config, or None when there is no config file."""
    path = config_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            cfg = json.load(f)
    except ValueError as e:
        raise SFError("config %s is not valid JSON: %s" % (path, e), 2)
    return _resolve(cfg)


def load() -> dict:
    cfg = try_load()
    if cfg is None:
        raise SFError("no config; copy factory.config.example.json to factory.config.json", 2)
    return cfg
