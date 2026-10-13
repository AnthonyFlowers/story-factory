from __future__ import annotations

from .. import config, jobs


def run(args):
    config.load()  # fail early (exit 2) when there is no config
    print(jobs.new_job(args.type, args.idea, mode=args.mode, jira_key=args.jira_key,
                       parent=args.parent, harness=args.harness))


def register(subparsers):
    p = subparsers.add_parser("new-job", help="create a job folder and print its id")
    p.add_argument("--type", required=True, choices=["story", "bug", "spike", "epic"])
    p.add_argument("--mode", choices=["new", "refine"], default="new")
    p.add_argument("--jira-key")
    p.add_argument("--parent")
    p.add_argument("--harness", choices=["claude", "copilot-lite"], default="claude")
    p.add_argument("--idea", required=True)
    p.set_defaults(func=run)
