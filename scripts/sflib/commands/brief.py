from __future__ import annotations

from .. import jobs


def run(args):
    print(jobs.write_brief(jobs.job_dir(args.id)))


def register(subparsers):
    p = subparsers.add_parser("brief", help="(re)write a job's brief.md")
    p.add_argument("id")
    p.set_defaults(func=run)
