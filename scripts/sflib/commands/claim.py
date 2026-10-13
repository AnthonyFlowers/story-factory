from __future__ import annotations

from .. import claims


def run_claim(args):
    ok, info = claims.claim(args.id, who=args.who, force=args.force)
    if ok:
        if info.get("took_over"):
            print("CLAIMED %s (took over a stale claim from %s, its process is gone)" % (args.id, info["took_over"]))
        else:
            print("CLAIMED %s" % args.id)
        return 0
    print("BUSY %s %s %s" % (args.id, info.get("who"), info.get("time")))
    return 3


def run_release(args):
    claims.release(args.id)
    print("RELEASED %s" % args.id)
    return 0


def register(subparsers):
    p = subparsers.add_parser("claim", help="claim a job so no other session drives it (exit 3 if busy)")
    p.add_argument("id")
    p.add_argument("--force", action="store_true", help="replace an existing claim")
    p.add_argument("--who", help="holder label (default <hostname>:<ppid>)")
    p.set_defaults(func=run_claim)
    r = subparsers.add_parser("release", help="release a job claim")
    r.add_argument("id")
    r.set_defaults(func=run_release)
