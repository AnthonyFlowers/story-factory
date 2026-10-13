from __future__ import annotations

import os

from .. import jobs


def human_section(text: str) -> str:
    """The `## For the human` section of a decision.md ('' when absent)."""
    out, on = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if on:
                break
            on = line.strip() == "## For the human"
        if on:
            out.append(line)
    return "\n".join(out).rstrip() + "\n" if out else ""


def run(args):
    path = os.path.join(jobs.job_dir(args.id), "decision.md")
    try:
        with open(path) as f:
            section = human_section(f.read())
    except OSError:
        section = ""
    print(section or "(no ## For the human section)", end="" if section else "\n")
    return 0


def register(subparsers):
    p = subparsers.add_parser("human", help="print the '## For the human' section of a job's decision.md")
    p.add_argument("id")
    p.set_defaults(func=run)
