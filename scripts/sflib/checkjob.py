"""Deterministic invariants for a finished job (sf.py check-job), plus the repo manifest
that proves the factory never modified team repos or team docs."""
from __future__ import annotations

import hashlib
import json
import os
import re

from . import claims, config, gate, jobs, schema, verdicts

TERMINAL = ("ready", "needs-human")
MAX_BYTES = 1024 * 1024
SKIP_DIRS = (".git", "node_modules")
MANIFEST = ".manifest.json"


def _read_json(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except OSError:
        return None, "missing"
    except ValueError as e:
        return None, "not valid JSON: %s" % e


def check_job(job_id: str, allow_running: bool = False) -> list:
    """Return [(ok, name, detail)] in check order."""
    out = []

    def add(ok, name, detail=""):
        out.append((bool(ok), name, detail))

    jp = jobs.job_dir(job_id)
    job, err = _read_json(os.path.join(jp, "job.json"))
    errs = [err] if err else schema.validate(job, schema.load_schema("job"))
    add(not errs, "job-schema", "; ".join(errs))
    if errs:
        return out

    stage = job["stage"]
    ok = stage in TERMINAL or (allow_running and job["type"] == "epic" and stage == "children")
    add(ok, "stage", "" if ok else "stage is %s (expected ready or needs-human%s)" % (
        stage, "; epics may be 'children' with --allow-running" if job["type"] == "epic" else ""))

    claim_file = os.path.exists(os.path.join(jp, claims.CLAIM))
    if stage in TERMINAL:
        bad = []
        if claim_file:
            bad.append(".claim file present")
        if job.get("claimed_by"):
            bad.append("claimed_by is %s" % job["claimed_by"])
        add(not bad, "claim", "; ".join(bad))

    story, err = _read_json(os.path.join(jp, "story.json"))
    serrs = [err] if err else schema.validate(story, schema.load_schema("story"))
    add(not serrs, "story-schema", "; ".join(serrs[:3]))

    if job["type"] == "epic":
        _epic(job, story if not serrs else None, allow_running, add)

    problems = []
    for n in range(1, job["round"] + 1):
        rd = os.path.join(jp, "round-%d" % n)
        for name in ("story.json", "checks.md"):
            if not os.path.isfile(os.path.join(rd, name)):
                problems.append("round-%d/%s missing" % (n, name))
        for lens in jobs.LENSES:
            f = os.path.join(rd, "review-%s.md" % lens)
            if not os.path.isfile(f):
                problems.append("round-%d/review-%s.md missing" % (n, lens))
                continue
            try:
                verdicts.parse_file(f, "review")
            except verdicts.Invalid as e:
                problems.append("round-%d/review-%s.md invalid (%s)" % (n, lens, e))
    add(not problems, "rounds", "; ".join(problems))

    reworks = len([x for x in os.listdir(jp) if re.match(r"^rework-.*\.md$", x)])
    add(job["round"] <= 2 + reworks, "round-limit",
        "" if job["round"] <= 2 + reworks else "round %d with %d rework file(s)" % (job["round"], reworks))

    dec_ok = True
    try:
        verdicts.parse_file(os.path.join(jp, "decision.md"), "decision")
    except verdicts.Invalid as e:
        dec_ok = False
        add(False, "decision-file", str(e))
    if dec_ok:
        add(True, "decision-file")

    if stage == "ready":
        why = []
        if job.get("decision") != "READY":
            why.append("decision is %s" % job.get("decision"))
        human = job.get("approved_by") == "human"
        if not human:
            res = gate.evaluate(job_id)
            if res["reasons"] or res["decision"] != "READY":
                why.append("gate says HUMAN: %s" % "; ".join(res["reasons"] or ["no-decision"]))
        add(not why, "ready", "; ".join(why))
        add(*_story_md(jp))
    elif stage == "needs-human":
        ok = bool(job.get("gate_reasons")) or _has_human_section(os.path.join(jp, "decision.md"))
        add(ok, "needs-human", "" if ok else
            "no '## For the human' numbered item in decision.md and gate_reasons is empty")

    big = []
    for dp, dn, fn in os.walk(jp):
        for name in fn:
            p = os.path.join(dp, name)
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    big.append(os.path.relpath(p, jp))
            except OSError:
                pass
    add(not big, "file-size", "over 1 MB: %s" % ", ".join(big))
    return out


def _story_md(jp):
    p = os.path.join(jp, "story.md")
    try:
        with open(p) as f:
            lines = f.read().splitlines()
    except OSError:
        return False, "story-md", "story.md missing"
    bad = []
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith("|") or re.match(r"^[-*+]\s+\[[ xX]\]", s):
            bad.append("%d (%s)" % (i, "table" if s.startswith("|") else "checkbox"))
        elif re.match(r"^\s+([-*+]|\d+\.)\s", ln):
            bad.append("%d (nested list)" % i)
    return not bad, "story-md", ("lines " + ", ".join(bad[:5])) if bad else ""


def _has_human_section(path):
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return False
    m = re.search(r"^## For the human\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return bool(m and re.search(r"^\s*\d+\.\s+\S", m.group(1), re.M))


def _epic(job, story, allow_running, add):
    children = job.get("children") or {}
    needs = (job["stage"] in TERMINAL and
             (job.get("decision") == "READY" or job.get("approved_by") == "human"))
    if job["stage"] == "children" or needs:
        if not children:
            add(False, "epic-children", "children map is empty")
            return
    elif not children:
        return
    bad = []
    if story:
        refs = {c["ref"] for c in story.get("epic", {}).get("children", [])}
        if refs != set(children):
            bad.append("children map refs %s differ from story refs %s" % (
                sorted(children), sorted(refs)))
    for ref, cid in sorted(children.items()):
        try:
            cj = jobs.load_job(cid)
        except Exception:
            bad.append("%s: job %s missing" % (ref, cid))
            continue
        if cj.get("parent") != job["id"]:
            bad.append("%s: parent is %s" % (cid, cj.get("parent")))
        if job["stage"] in TERMINAL and cj.get("stage") not in TERMINAL:
            bad.append("%s still %s" % (cid, cj.get("stage")))
    add(not bad, "epic-children", "; ".join(bad))


def format_results(results) -> list:
    lines = []
    for ok, name, detail in results:
        lines.append("OK %s" % name if ok else "FAIL %s: %s" % (name, detail))
    lines.append("RESULT: %s" % ("PASS" if all(r[0] for r in results) else "FAIL"))
    return lines


# ---- manifest -------------------------------------------------------------

def _roots() -> list:
    cfg = config.load()
    return sorted({e["path"] for key in ("repos", "team_docs") for e in cfg.get(key, []) if e.get("path")})


def build_manifest() -> dict:
    files = {}
    for root in _roots():
        if not os.path.isdir(root):
            continue
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for name in fn:
                p = os.path.join(dp, name)
                h = hashlib.sha256()
                try:
                    with open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(1 << 20), b""):
                            h.update(chunk)
                except OSError:
                    continue
                files[p] = h.hexdigest()
    return {"roots": _roots(), "files": files}


def manifest_path() -> str:
    return os.path.join(config.jobs_dir(), MANIFEST)


def write_manifest() -> int:
    m = build_manifest()
    os.makedirs(config.jobs_dir(), exist_ok=True)
    jobs.atomic_write(manifest_path(), json.dumps(m, indent=1) + "\n")
    return len(m["files"])


def compare_manifest():
    """Return (diff lines, count). Raises FileNotFoundError when no manifest was written."""
    with open(manifest_path()) as f:
        old = json.load(f)
    new = build_manifest()
    diff = []
    for p in sorted(set(old["files"]) | set(new["files"])):
        a, b = old["files"].get(p), new["files"].get(p)
        if a is None:
            diff.append("ADDED %s" % p)
        elif b is None:
            diff.append("REMOVED %s" % p)
        elif a != b:
            diff.append("CHANGED %s" % p)
    if old.get("roots") != new["roots"]:
        diff.append("CONFIG roots changed since the manifest was written")
    return diff, len(new["files"])
