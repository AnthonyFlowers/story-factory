from __future__ import annotations

from .. import backlog


def run_claim(args):
    got = backlog.claim()
    if got:
        print("%d\t%s\t%s" % got)
    return 0


def run_done(args):
    backlog.done(args.line, args.id)
    print("done %d %s" % (args.line, args.id))
    return 0


def register(subparsers):
    p = subparsers.add_parser("backlog", help="claim or finish items in factory/backlog.md")
    sub = p.add_subparsers(dest="backlog_cmd", metavar="ACTION")
    sub.required = True
    c = sub.add_parser("claim", help="claim the first unchecked item; prints LINE<TAB>TYPE<TAB>TEXT or nothing")
    c.set_defaults(func=run_claim)
    d = sub.add_parser("done", help="record the job id on a claimed item")
    d.add_argument("line", type=int)
    d.add_argument("id")
    d.set_defaults(func=run_done)
