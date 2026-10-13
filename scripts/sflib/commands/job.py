from __future__ import annotations

import json

from .. import jobs


def run(args):
    job = jobs.update_job(
        args.id, stage=args.stage, round_=args.round, reset_reviews=args.reset_reviews,
        reviews=args.review, revisions_used=args.revisions_used, flags=args.flags,
        decision=args.decision, approved_by=args.approved_by, sets=args.set)
    print(json.dumps(job, indent=2))


def register(subparsers):
    p = subparsers.add_parser("job", help="update a job's job.json")
    p.add_argument("id")
    p.add_argument("--stage")
    p.add_argument("--round", type=int)
    p.add_argument("--reset-reviews", action="store_true")
    p.add_argument("--review", action="append", metavar="LENS=VALUE")
    p.add_argument("--revisions-used", type=int)
    p.add_argument("--flags", help="comma-separated")
    p.add_argument("--decision")
    p.add_argument("--approved-by")
    p.add_argument("--set", action="append", metavar="KEY=JSONVALUE")
    p.set_defaults(func=run)
