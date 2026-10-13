#!/usr/bin/env python3
"""story-factory CLI: a thin dispatcher. Each subcommand lives in
sflib/commands/<name>.py and exposes register(subparsers)."""
from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sflib import SFError  # noqa: E402
from sflib import commands  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sf.py", description="story-factory CLI")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    for info in sorted(pkgutil.iter_modules(commands.__path__), key=lambda i: i.name):
        mod = importlib.import_module("sflib.commands." + info.name)
        if hasattr(mod, "register"):
            mod.register(sub)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rc = args.func(args)
    except SFError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return e.code
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
