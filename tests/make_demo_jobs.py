#!/usr/bin/env python3
"""Write 8 fake jobs (all DEMO data) into OUT_DIR/jobs/ and copy factory/dashboard.html to OUT_DIR."""
from __future__ import annotations

import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TS = "2026-10-13T09:00:00Z"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def story_json(title):
    return json.dumps({"title": title, "type": "story"}, indent=2) + "\n"


def story_md(title):
    return ("# %s\n\n**As a** customer **I want** a clear statement **so that** I can reconcile.\n\n"
            "## Acceptance criteria\n\n- [ ] Filter by date range\n- [x] Default is last 30 days\n  - nested item\n\n"
            "| Field | Type |\n|---|---|\n| from | date |\n| to | date |\n\n> Repo: `accounts-api`\n\n"
            "```\nGET /accounts/{id}/statements?from=&to=\n```\n" % title)


def review(lens, verdict, flags=""):
    return "VERDICT: %s\nFLAGS: %s\n\nNotes for the %s lens.\n" % (verdict, flags, lens)


def job(jid, typ, stage, rnd, title, no_title=False, **kw):
    j = {"id": jid, "type": typ, "mode": "new", "harness": "claude", "idea": title, "jira_key": None,
         "parent": None, "children": {}, "title": title, "stage": stage, "round": rnd,
         "revisions_used": 0, "reviews": {}, "flags": [], "decision": None, "approved_by": None,
         "gate_reasons": [], "writer_agent": None, "claimed_by": None, "created": TS, "updated": TS}
    j.update(kw)
    if no_title:
        j["title"] = None
    return j


def put(out, j, story=True):
    d = os.path.join(out, "jobs", j["id"])
    write(os.path.join(d, "job.json"), json.dumps(j, indent=2) + "\n")
    write(os.path.join(d, "brief.md"), "# Brief\n\n%s\n" % j["idea"])
    if story:
        write(os.path.join(d, "story.json"), story_json(j["title"]))
        write(os.path.join(d, "story.md"), story_md(j["title"]))
    return d


def main(out):
    out = os.path.abspath(out)
    os.makedirs(os.path.join(out, "jobs"), exist_ok=True)
    allpass = {"invest": "PASS", "ac": "PASS", "tech": "PASS", "security": "PASS"}

    put(out, job("001-intake-demo", "story", "intake", 0, "Show account nickname on statements", no_title=True), story=False)
    put(out, job("002-draft-demo", "bug", "draft", 1, "Statement total rounds incorrectly"))

    d = put(out, job("003-review-demo", "story", "review", 1, "Export transactions as CSV",
                     reviews={"invest": "PASS", "ac": "CHANGES", "tech": "pending", "security": "INVALID"}))
    for lens, v in (("invest", "PASS"), ("ac", "CHANGES")):
        write(os.path.join(d, "round-1", "review-%s.md" % lens), review(lens, v))
    write(os.path.join(d, "round-1", "checks.md"), "# Checks\n\n- [x] schema valid\n")

    d = put(out, job("004-refine-demo-101", "story", "review", 2, "Filter account statements by date range",
                     mode="refine", jira_key="DEMO-101", revisions_used=1, flags=["pii", "audit"],
                     reviews={"invest": "PASS", "ac": "PASS", "tech": "pending", "security": "CHANGES"},
                     claimed_by="a1b2"))
    for lens, v in (("invest", "PASS"), ("ac", "CHANGES"), ("tech", "PASS"), ("security", "CHANGES")):
        write(os.path.join(d, "round-1", "review-%s.md" % lens), review(lens, v, "pii" if lens == "security" else ""))
    write(os.path.join(d, "round-1", "checks.md"), "# Checks\n\n- [x] schema valid\n")
    write(os.path.join(d, "round-1", "story.json"), story_json("Filter statements"))
    write(os.path.join(d, "rework-1.md"), "# Rework 1\n\nTighten the second criterion.\n")
    write(os.path.join(d, "context", "jira", "DEMO-101.json"), json.dumps({"key": "DEMO-101", "fields": {"summary": "Filter statements"}}, indent=2))

    d = put(out, job("005-approve-demo", "spike", "approve", 1, "Evaluate PDF generation libraries", reviews=allpass))
    for lens in allpass:
        write(os.path.join(d, "round-1", "review-%s.md" % lens), review(lens, "PASS"))

    d = put(out, job("006-ready-demo", "story", "ready", 1, "Add pagination to accounts-api listing",
                     reviews=allpass, decision="READY", approved_by="agent", flags=["audit"]))
    write(os.path.join(d, "decision.md"), "READY\nFLAGS: audit\n\nAll lenses passed.\n")

    d = put(out, job("007-needs-human-demo", "story", "needs-human", 1, "Store card holder name for refunds",
                     reviews=allpass, decision="NEEDS-HUMAN", flags=["pii", "auth"],
                     gate_reasons=["flag pii requires a human", "flag auth requires a human"]))
    write(os.path.join(d, "decision.md"), "NEEDS-HUMAN\nFLAGS: pii,auth\n\n- flag pii requires a human\n- flag auth requires a human\n")

    put(out, job("008-epic-demo", "epic", "children", 1, "Statements overhaul",
                 reviews=allpass, decision="READY", approved_by="agent",
                 children={"009-child-ready": "ready", "010-child-draft": "draft"}))


    shutil.copyfile(os.path.join(REPO, "factory", "dashboard.html"), os.path.join(out, "dashboard.html"))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: make_demo_jobs.py OUT_DIR")
    main(sys.argv[1])
