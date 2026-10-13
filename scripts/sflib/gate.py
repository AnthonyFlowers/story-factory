"""The bank escalation floor: deterministic reasons a story must go to a human."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
from types import SimpleNamespace

from . import SFError, checks, config, jobs, template, verdicts


def latest_round(job_path: str) -> int:
    best = 0
    for name in os.listdir(job_path):
        m = re.match(r"^round-(\d+)$", name)
        if m and os.path.isdir(os.path.join(job_path, name)):
            best = max(best, int(m.group(1)))
    return best


def evaluate(job_id: str) -> dict:
    """Return {"reasons": [...], "flags": [...], "decision": READY|NEEDS-HUMAN|None}."""
    jp = jobs.job_dir(job_id)
    cfg = config.try_load() or config._resolve({})
    esc = cfg["escalation"]
    blocking = esc.get("always_human", config.DEFAULT_ALWAYS_HUMAN)
    reasons, flags = [], []

    story_path = os.path.join(jp, "story.json")
    story, story_text = {}, ""
    try:
        with open(story_path) as f:
            story_text = f.read()
        story = json.loads(story_text)
    except (OSError, ValueError):
        reasons.append("schema-errors")
    for f in story.get("risk_flags") or []:
        flags.append(f)

    if story:
        tpl = template.load_template(cfg.get("template", "default"))
        res = checks.compute(jp, story, cfg, tpl)
        if res["schema_errors"]:
            reasons.append("schema-errors")
        if any(s == "MISSING" for s, _ in res["sources"] + res["api"]):
            reasons.append("missing-sources")
        if story.get("open_questions"):
            reasons.append("open-questions")
        if any(a.get("kind") == "product" for a in story.get("assumptions") or []):
            reasons.append("product-assumption")
        low = story_text.lower()
        for term in esc.get("extra_terms", []):
            if term and term.lower() in low:
                reasons.append("term:%s" % term)

    rnd = latest_round(jp)
    for lens in jobs.LENSES:
        p = os.path.join(jp, "round-%d" % rnd, "review-%s.md" % lens)
        try:
            verdict, fl = verdicts.parse_file(p, "review")
        except verdicts.Invalid:
            reasons.append("review-invalid:%s" % lens)
            continue
        flags += fl
        if verdict == "CHANGES":
            reasons.append("changes-left:%s" % lens)

    decision = None
    try:
        decision, fl = verdicts.parse_file(os.path.join(jp, "decision.md"), "decision")
        flags += fl
    except verdicts.Invalid:
        reasons.append("no-decision")
    if decision == "NEEDS-HUMAN":
        reasons.append("decision-needs-human")

    flags = [f for f in verdicts.FLAGS if f in flags]
    for f in flags:
        if f in blocking:
            reasons.append("flag:%s" % f)
    seen = []
    for r in reasons:
        if r not in seen:
            seen.append(r)
    # flags first, as the spec lists them
    seen.sort(key=lambda r: 0 if r.startswith("flag:") else 1)
    return {"reasons": seen, "flags": flags, "decision": decision}


def apply(job_id: str, result: dict) -> str:
    reasons = result["reasons"]
    if result["decision"] == "READY" and not reasons:
        jobs.update_job(job_id, stage="ready", decision="READY", approved_by="agent",
                        flags=",".join(result["flags"]), sets=["gate_reasons=[]"])
    else:
        jobs.update_job(job_id, stage="needs-human", decision="NEEDS-HUMAN", approved_by="none",
                        flags=",".join(result["flags"]),
                        sets=["gate_reasons=" + json.dumps(reasons)])
    try:
        from .commands import render
        with contextlib.redirect_stdout(io.StringIO()):
            render.run(SimpleNamespace(target=job_id, format="md", out=None))
    except SFError:
        pass  # invalid story: the gate already recorded schema-errors
    return jobs.load_job(job_id)["stage"]
