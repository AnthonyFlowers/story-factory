"""Deterministic per-round checks: schema, definition of ready (auto), sources, API operations."""
from __future__ import annotations

import json
import os
import re
import shutil

from . import SFError, config, jobs, schema, template

SRC_RE = re.compile(r"^([A-Za-z0-9_.-]+):(.+?)(?::(\d+)(?:-\d+)?)?$")


def _name_paths(cfg: dict) -> dict:
    out = {}
    for entry in list(cfg.get("repos", [])) + list(cfg.get("team_docs", [])):
        if "name" in entry and "path" in entry:
            out[entry["name"]] = entry["path"]
    return out


def _resolve_file(names: dict, ref: str):
    """Return (status, detail). status is OK, MISSING or BADREF."""
    m = SRC_RE.match(ref)
    if not m:
        return "BADREF", "not <name>:<path>[:<line>]"
    name, rel, line = m.group(1), m.group(2), m.group(3)
    if name not in names:
        return "MISSING", "no repo or doc named %s in config" % name
    base = os.path.realpath(names[name])
    full = os.path.realpath(os.path.join(base, rel))
    if full != base and not full.startswith(base + os.sep):
        return "MISSING", "path escapes %s" % name
    if not os.path.isfile(full):
        return "MISSING", "file not found"
    if line:
        try:
            with open(full, errors="replace") as f:
                n = sum(1 for _ in f)
        except OSError:
            return "MISSING", "cannot read"
        if int(line) > n or int(line) < 1:
            return "MISSING", "line %s beyond end of file (%d lines)" % (line, n)
    return "OK", full


def _jira_files(job_path: str) -> list:
    d = os.path.join(job_path, "context", "jira")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def _operation_exists(spec: dict, operation: str) -> bool:
    method, path = operation.split(" ", 1)
    item = (spec.get("paths") or {}).get(path)
    return isinstance(item, dict) and method.lower() in item


def compute(job_path: str, story: dict, cfg: dict, tpl: dict) -> dict:
    """Run every check on a parsed story. Returns a dict used by render_md and by the gate."""
    names = _name_paths(cfg)
    nothing_configured = not names
    res = {"schema_errors": schema.validate(story, schema.load_schema("story")),
           "dor": [], "sources": [], "api": [], "flags": list(story.get("risk_flags") or [])}
    stype = story.get("type")
    jira_files = _jira_files(job_path)

    # Sources
    for s in story.get("sources") or []:
        kind, ref = s.get("kind"), s.get("ref", "")
        if kind in ("idea", "rework"):
            res["sources"].append(("SKIPPED", "%s (%s)" % (ref, kind)))
        elif kind == "jira":
            if any(ref.lower() in f.lower() for f in jira_files):
                res["sources"].append(("SKIPPED", "%s (jira: present in context/jira)" % ref))
            else:
                res["sources"].append(("MISSING", "%s (jira: not pulled)" % ref))
        elif nothing_configured:
            res["sources"].append(("SKIPPED", "%s (no repos or team docs configured)" % ref))
        else:
            status, detail = _resolve_file(names, ref)
            if status == "OK":
                res["sources"].append(("OK", ref))
            else:
                res["sources"].append(("MISSING", "%s (%s)" % (ref, detail)))

    # API operations
    for a in story.get("api_impact") or []:
        contract, op, change = a.get("contract", ""), a.get("operation", ""), a.get("change", "")
        label = "%s in %s (%s" % (op, contract, change)
        if contract.endswith((".yaml", ".yml")):
            res["api"].append(("SKIPPED", "%s (yaml)" % contract))
            continue
        if nothing_configured:
            res["api"].append(("SKIPPED", "%s in %s (no repos or team docs configured)" % (op, contract)))
            continue
        status, full = _resolve_file(names, contract)
        if status != "OK":
            res["api"].append(("MISSING", "%s; contract: %s)" % (label, full)))
            continue
        try:
            with open(full) as f:
                spec = json.load(f)
        except (OSError, ValueError):
            res["api"].append(("MISSING", "%s; contract is not readable JSON)" % label))
            continue
        if not re.match(r"^(GET|POST|PUT|PATCH|DELETE) /", op):
            res["api"].append(("MISSING", "%s; bad operation)" % label))
            continue
        exists = _operation_exists(spec, op)
        if change == "add":
            if exists:
                res["api"].append(("CONFLICT", "%s; already exists)" % label))
            else:
                res["api"].append(("NEW", "%s; not in contract, as expected)" % label))
        elif exists:
            res["api"].append(("OK", "%s)" % label))
        else:
            res["api"].append(("MISSING", "%s; operation not found)" % label))

    # Definition of ready (auto)
    n_ac = len(story.get("acceptance_criteria") or [])
    for item in tpl.get("definition_of_ready", []):
        check = item.get("check", "")
        if not check.startswith("auto:"):
            continue
        name, text = check[5:], item["text"]
        ok, why = True, ""
        if name == "user_story":
            if stype == "story":
                us = story.get("user_story") or {}
                ok = all(us.get(k) for k in ("as_a", "i_want", "so_that"))
                why = "user_story incomplete"
        elif name == "ac_count":
            need = {"story": 2, "bug": 2, "spike": 1}.get(stype, 0)
            ok = n_ac >= need
            why = "%d ACs, need %d" % (n_ac, need)
        elif name == "api_refs":
            bad = 0
            for a in story.get("api_impact") or []:
                if not a.get("operation"):
                    bad += 1
                elif not nothing_configured and _resolve_file(names, a.get("contract", ""))[0] != "OK" \
                        and not a.get("contract", "").endswith((".yaml", ".yml")):
                    bad += 1
            ok = bad == 0
            why = "%d api_impact items without an operation or resolvable contract" % bad
        elif name == "sources_exist":
            bad = sum(1 for st, _ in res["sources"] if st == "MISSING")
            ok = bad == 0
            why = "%d missing sources" % bad
        elif name == "no_open_questions":
            n = len(story.get("open_questions") or [])
            ok = n == 0
            why = "%d open questions" % n
        else:
            res["dor"].append(("SKIPPED", "%s %s (unknown check)" % (item["id"], text)))
            continue
        res["dor"].append(("PASS", "%s %s" % (item["id"], text)) if ok
                          else ("FAIL", "%s %s: %s" % (item["id"], text, why)))
    return res


def counts(res: dict) -> tuple:
    dor_fail = sum(1 for s, _ in res["dor"] if s == "FAIL")
    missing = sum(1 for s, _ in res["sources"] + res["api"] if s == "MISSING")
    return dor_fail, missing


def render_md(res: dict, round_: int) -> str:
    L = ["# Checks: round %d" % round_,
         "Schema: %s" % ("ERRORS" if res["schema_errors"] else "OK")]
    for e in res["schema_errors"]:
        L.append("- ERROR %s" % e)
    L += ["## Definition of ready (auto)"] + ["- %s %s" % x for x in res["dor"]]
    L += ["## Sources"] + ["- %s %s" % x for x in res["sources"]]
    L += ["## API operations"] + ["- %s %s" % x for x in res["api"]]
    L += ["## Flags", "risk_flags: %s" % (", ".join(res["flags"]) or "none"), ""]
    return "\n".join(L)


def run_checks(job_id: str, round_: int) -> tuple:
    """Snapshot story.json to round-N/ and write checks.md. Returns (schema_ok, dor_fail, missing)."""
    jp = jobs.job_dir(job_id)
    src = os.path.join(jp, "story.json")
    if not os.path.isfile(src):
        raise SFError("job %s has no story.json" % job_id)
    rd = os.path.join(jp, "round-%d" % round_)
    os.makedirs(rd, exist_ok=True)
    shutil.copyfile(src, os.path.join(rd, "story.json"))
    cfg = config.try_load() or config._resolve({})
    tpl = template.load_template(cfg.get("template", "default"))
    try:
        with open(src) as f:
            story = json.load(f)
    except ValueError as e:
        text = "# Checks: round %d\nSchema: ERRORS\n- ERROR : not valid JSON: %s\n" % (round_, e)
        jobs.atomic_write(os.path.join(rd, "checks.md"), text)
        return False, 0, 0
    res = compute(jp, story, cfg, tpl)
    jobs.atomic_write(os.path.join(rd, "checks.md"), render_md(res, round_))
    dor_fail, missing = counts(res)
    return not res["schema_errors"], dor_fail, missing
