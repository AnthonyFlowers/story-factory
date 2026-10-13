from __future__ import annotations

from .. import config, doctor


def run(args):
    problems = doctor.check(config.root())
    if not problems:
        print("OK")
        return 0
    for p in problems:
        print("PROBLEM: %s" % p)
    return 1


def register(subparsers):
    p = subparsers.add_parser("doctor", help="check repo hygiene")
    p.set_defaults(func=run)
