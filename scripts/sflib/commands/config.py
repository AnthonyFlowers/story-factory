from __future__ import annotations

import json

from .. import config


def run(args):
    print(json.dumps(config.load(), indent=2))


def register(subparsers):
    p = subparsers.add_parser("config", help="print the resolved config as JSON")
    p.set_defaults(func=run)
