from __future__ import annotations

from .. import gate


def run(args):
    result = gate.evaluate(args.id)
    if result["reasons"] or result["decision"] != "READY":
        print("HUMAN: %s" % "; ".join(result["reasons"] or ["no-decision"]))
    else:
        print("OK")
    if args.apply:
        print(gate.apply(args.id, result))
    return 0


def register(subparsers):
    p = subparsers.add_parser("gate", help="compute the bank escalation floor for a job")
    p.add_argument("id")
    p.add_argument("--apply", action="store_true", help="write the result into job.json and render story.md")
    p.set_defaults(func=run)
