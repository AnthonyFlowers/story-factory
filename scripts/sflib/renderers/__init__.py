from __future__ import annotations

import importlib
import pkgutil

from .. import SFError


def get(fmt: str):
    """Return the renderer module whose FORMAT matches fmt."""
    for info in pkgutil.iter_modules(__path__):
        mod = importlib.import_module("%s.%s" % (__name__, info.name))
        if getattr(mod, "FORMAT", None) == fmt:
            return mod
    raise SFError("no renderer for format %r" % fmt, 2)
