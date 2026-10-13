from __future__ import annotations

from .. import config, jira, jobs


def run(args):
    cfg = config.try_load() or config._resolve({})
    for k in jira.keys_to_pull(jobs.load_job(args.id), jobs.job_dir(args.id), cfg):
        print(k)


def register(subparsers):
    p = subparsers.add_parser("jira-keys", help="print the Jira keys still to pull for a job")
    p.add_argument("id")
    p.set_defaults(func=run)
