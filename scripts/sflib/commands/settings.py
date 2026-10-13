from __future__ import annotations

from .. import config, settings


def run(args):
    print(settings.write(config.load()))


def register(subparsers):
    p = subparsers.add_parser("settings", help="write .claude/settings.local.json from the config")
    p.set_defaults(func=run)
