from __future__ import annotations

from .. import verdicts


def run(args):
    try:
        verdict, flags = verdicts.parse_file(args.file)
    except verdicts.Invalid as e:
        print("INVALID %s" % e)
        return 1
    print("%s flags=%s" % (verdict, ",".join(flags) or "none"))
    return 0


def register(subparsers):
    p = subparsers.add_parser("verdict", help="parse a review or decision file")
    p.add_argument("file")
    p.set_defaults(func=run)
