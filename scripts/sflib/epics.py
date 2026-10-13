"""Epic breakdown helpers: spawn child jobs, report status, hand out the next child.

Children run in parallel sessions; the per-job claim (claims.py) is the only lock.
"""
from __future__ import annotations

import json
import os

from . import SFError, claims, jobs

TERMINAL = ("ready", "needs-human")


def load_epic(epic_id: str):
    """Return (job, story, story_path) for an epic job."""
    job = jobs.load_job(epic_id)
    path = os.path.join(jobs.job_dir(epic_id), "story.json")
    try:
        with open(path) as f:
            story = json.load(f)
    except (OSError, ValueError) as e:
        raise SFError("epic %s has no readable story.json: %s" % (epic_id, e))
    if story.get("type") != "epic" or job.get("type") != "epic":
        raise SFError("%s is not an epic" % epic_id)
    return job, story, os.path.abspath(path)


def _children(story: dict) -> list:
    return story.get("epic", {}).get("children", [])


def topo_order(children: list) -> list:
    """Children in dependency order, ties broken by `order` then input position.
    Raises SFError (exit 1) on an unknown ref or a cycle."""
    by_ref = {}
    for c in children:
        if c["ref"] in by_ref:
            raise SFError("duplicate child ref %s" % c["ref"], 1)
        by_ref[c["ref"]] = c
    for c in children:
        for d in c.get("depends_on", []):
            if d not in by_ref:
                raise SFError("child %s depends on unknown ref %s" % (c["ref"], d), 1)
    # cycle detection (DFS) so the message can show the path
    state = {}

    def visit(ref, path):
        if state.get(ref) == 2:
            return
        if state.get(ref) == 1:
            cyc = path[path.index(ref):] + [ref]
            raise SFError("dependency cycle " + " -> ".join(cyc), 1)
        state[ref] = 1
        for d in by_ref[ref].get("depends_on", []):
            visit(d, path + [ref])
        state[ref] = 2

    for c in sorted(children, key=lambda c: (c.get("order", 0), c["ref"])):
        visit(c["ref"], [])
    done, out = set(), []
    pending = sorted(children, key=lambda c: (c.get("order", 0), c["ref"]))
    while pending:
        for c in pending:
            if all(d in done for d in c.get("depends_on", [])):
                out.append(c)
                done.add(c["ref"])
                pending.remove(c)
                break
    return out


def _idea(child, epic_id, story, story_path, by_ref):
    deps = [d + " → " + by_ref[d]["title"] for d in child.get("depends_on", [])]
    return "%s. %s\n(Child %s of epic %s: %s. Epic story: %s. Depends on: %s.)" % (
        child["title"], child["summary"], child["ref"], epic_id, story["title"], story_path,
        ", ".join(deps) if deps else "none")


def spawn_children(epic_id: str) -> list:
    """Create one job per child. Returns [(ref, job_id)] in creation order."""
    job, story, story_path = load_epic(epic_id)
    children = _children(story)
    ordered = topo_order(children)
    existing = dict(job.get("children") or {})
    if existing and all(c["ref"] in existing for c in ordered):
        return list(existing.items())
    if not (job["stage"] == "ready" or (job["stage"] == "needs-human" and job.get("approved_by") == "human")):
        if job["stage"] != "children":
            raise SFError("epic %s is in stage %s" % (epic_id, job["stage"]), 1)
    by_ref = {c["ref"]: c for c in children}
    jira_key = job.get("jira_key")
    for c in ordered:
        if c["ref"] in existing:
            continue
        cid = jobs.new_job(c["type"], _idea(c, epic_id, story, story_path, by_ref), jira_key=jira_key,
                           parent=epic_id, slug_text=c["title"])
        existing[c["ref"]] = cid
        # Save the map after every child so an interrupted run resumes instead of duplicating.
        jobs.update_job(epic_id, sets=["children=" + json.dumps(existing)])
        jobs.write_brief(jobs.job_dir(cid))  # now the parent map knows this child's ref
        claims.release(cid)  # no-op unless something claimed it; any session may pick it up
    jobs.update_job(epic_id, stage="children", sets=["children=" + json.dumps(existing)])
    claims.release(epic_id)
    return [(c["ref"], existing[c["ref"]]) for c in ordered]


def child_rows(epic_id: str) -> list:
    """[(ref, job_id, stage, claimed_by)] in epic order."""
    job, story, _ = load_epic(epic_id)
    children = job.get("children") or {}
    if not children:
        raise SFError("epic %s has no child jobs yet; run spawn-children" % epic_id, 1)
    order = {c["ref"]: i for i, c in enumerate(topo_order(_children(story)))}
    rows = []
    for ref in sorted(children, key=lambda r: order.get(r, 999)):
        cj = jobs.load_job(children[ref])
        who = (claims.read_claim(children[ref]) or {}).get("who") if os.path.exists(
            os.path.join(jobs.job_dir(children[ref]), claims.CLAIM)) else None
        rows.append((ref, children[ref], cj["stage"], who))
    return rows


def epic_status(epic_id: str, apply: bool = False) -> dict:
    rows = child_rows(epic_id)
    terminal = all(r[2] in TERMINAL for r in rows)
    ready = sum(1 for r in rows if r[2] == "ready")
    human = [r[1] for r in rows if r[2] == "needs-human"]
    result = {"rows": rows, "done": terminal, "ready": ready, "needs_human": len(human), "stage": None}
    if apply and terminal:
        if human:
            stage, reasons = "needs-human", ["children-need-human:" + ",".join(human)]
        else:
            stage, reasons = "ready", []
        jobs.update_job(epic_id, stage=stage, sets=["gate_reasons=" + json.dumps(reasons)])
        result["stage"] = stage
    return result


def next_child(epic_id: str, who=None):
    """Atomically claim and return the id of the next child to run, or None."""
    job, story, _ = load_epic(epic_id)
    children = job.get("children") or {}
    meta = {c["ref"]: c for c in _children(story)}
    stages = {}
    for ref, cid in children.items():
        stages[ref] = jobs.load_job(cid)["stage"]
    cands = []
    for ref, cid in children.items():
        if stages[ref] in TERMINAL:
            continue
        if os.path.exists(os.path.join(jobs.job_dir(cid), claims.CLAIM)):
            continue
        deps = meta.get(ref, {}).get("depends_on", [])
        blocked = any(stages.get(d) not in TERMINAL for d in deps)
        cands.append((blocked, meta.get(ref, {}).get("order", 999), ref, cid))
    for _blocked, _order, _ref, cid in sorted(cands):
        ok, _info = claims.claim(cid, who=who)
        if not ok:
            continue  # lost a race; try the next candidate
        if jobs.load_job(cid)["stage"] in TERMINAL:  # finished between listing and claiming
            claims.release(cid)
            continue
        return cid
    return None
