from __future__ import annotations

import json
import os

from . import SFError, config


def load_template(name: str = "default") -> dict:
    """templates/<name>.json first, then templates/local/<name>.json."""
    base = os.path.join(config.root(), "templates")
    for path in (os.path.join(base, name + ".json"), os.path.join(base, "local", name + ".json")):
        if os.path.isfile(path):
            with open(path) as f:
                return json.load(f)
    raise SFError("template %r not found in templates/ or templates/local/" % name)
