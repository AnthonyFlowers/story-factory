from __future__ import annotations

from .. import jobs


def run(args):
    for j in jobs.list_jobs():
        text = (j.get("title") or j.get("idea") or "").replace("\n", " ")[:60]
        print("%s  %s  %s  r%s  %s" % (j["id"], j["type"], j["stage"], j["round"], text))


def register(subparsers):
    p = subparsers.add_parser("list", help="list jobs")
    p.set_defaults(func=run)
