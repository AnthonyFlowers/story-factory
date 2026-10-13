from __future__ import annotations

from .. import epics


def run_spawn(args):
    for ref, cid in epics.spawn_children(args.id):
        print("%s\t%s" % (ref, cid))


def run_status(args):
    res = epics.epic_status(args.id, apply=args.apply)
    for ref, cid, stage, who in res["rows"]:
        print("%s  %s  %s%s" % (ref, cid, stage, ("  claimed_by=%s" % who) if who else ""))
    if res["done"]:
        print("ALL-DONE ready=%d needs-human=%d" % (res["ready"], res["needs_human"]))
    else:
        print("RUNNING")
    if res["stage"]:
        print("epic stage: %s" % res["stage"])


def run_next(args):
    cid = epics.next_child(args.id, who=args.who)
    if cid:
        print(cid)


def register(subparsers):
    p = subparsers.add_parser("spawn-children", help="create one job per epic child (idempotent)")
    p.add_argument("id")
    p.set_defaults(func=run_spawn)
    s = subparsers.add_parser("epic-status", help="show child stages; --apply sets the epic stage when all are done")
    s.add_argument("id")
    s.add_argument("--apply", action="store_true")
    s.set_defaults(func=run_status)
    n = subparsers.add_parser("next-child", help="claim and print the next child job to run (nothing if none left)")
    n.add_argument("id")
    n.add_argument("--who")
    n.set_defaults(func=run_next)
