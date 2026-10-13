from __future__ import annotations

from .. import checks


def run(args):
    ok, dor_fail, missing = checks.run_checks(args.id, args.round)
    print("checks: schema=%s dor_fail=%d missing=%d" % ("OK" if ok else "ERRORS", dor_fail, missing))
    return 0


def register(subparsers):
    p = subparsers.add_parser("checks", help="snapshot story.json into round-N/ and write checks.md")
    p.add_argument("id")
    p.add_argument("--round", type=int, required=True)
    p.set_defaults(func=run)
