from __future__ import annotations

import os

from .. import claims, jobs


def run(args):
    jp = jobs.job_dir(args.id)
    text = "NEEDS-HUMAN\nFLAGS: none\n\n## Why\n%s\n\n## For the human\n1. %s\n" % (args.why, args.why)
    jobs.atomic_write(os.path.join(jp, "decision.md"), text)
    jobs.update_job(args.id, stage="needs-human", decision="NEEDS-HUMAN")
    claims.release(args.id)
    print("needs-human")
    return 0


def register(subparsers):
    p = subparsers.add_parser("escalate", help="write a NEEDS-HUMAN decision.md and set the job stage")
    p.add_argument("id")
    p.add_argument("--why", required=True)
    p.set_defaults(func=run)
