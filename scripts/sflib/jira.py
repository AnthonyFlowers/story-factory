from __future__ import annotations

import json
import os
import re

KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+-[0-9]+$")
KEY_FIND = re.compile(r"\b[A-Z][A-Z0-9_]+-[0-9]+\b")


def find_keys(text: str) -> list:
    """Distinct issue keys in text, in order of first appearance."""
    out = []
    for k in KEY_FIND.findall(text or ""):
        if k not in out:
            out.append(k)
    return out


def adf_to_text(node) -> str:
    """Flatten an Atlassian Document Format value to plain text, newline between blocks."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(t for t in (adf_to_text(n) for n in node) if t != "")
    if not isinstance(node, dict):
        return ""
    typ = node.get("type")
    if typ == "text":
        return node.get("text", "")
    if typ == "hardBreak":
        return "\n"
    content = node.get("content") or []
    if typ in ("paragraph", "heading", "codeBlock", "mention", "emoji") or all(
            isinstance(c, dict) and c.get("type") in ("text", "hardBreak", "mention", "emoji", "inlineCard")
            for c in content):
        return "".join(adf_to_text(c) for c in content)
    return adf_to_text(content)


def _name(v):
    return v.get("name") if isinstance(v, dict) else v


def from_rest(raw: dict) -> dict:
    f = raw.get("fields") or {}
    desc = f.get("description")
    if isinstance(desc, (dict, list)):
        desc = adf_to_text(desc)
    parent = f.get("parent")
    links = []
    for il in f.get("issuelinks") or []:
        t = il.get("type") or {}
        if il.get("outwardIssue"):
            links.append({"relation": t.get("outward") or t.get("name") or "relates to",
                          "key": il["outwardIssue"].get("key")})
        elif il.get("inwardIssue"):
            links.append({"relation": t.get("inward") or t.get("name") or "relates to",
                          "key": il["inwardIssue"].get("key")})
    return {
        "key": raw.get("key"),
        "issue_type": _name(f.get("issuetype")),
        "summary": f.get("summary"),
        "status": _name(f.get("status")),
        "description": desc if desc is not None else "",
        "acceptance_criteria": None,
        "labels": list(f.get("labels") or []),
        "components": [_name(c) for c in f.get("components") or []],
        "fix_versions": [_name(v) for v in f.get("fixVersions") or []],
        "parent_key": parent.get("key") if isinstance(parent, dict) else None,
        "links": [l for l in links if l["key"]],
        "subtasks": [s.get("key") for s in f.get("subtasks") or [] if isinstance(s, dict) and s.get("key")],
        "updated": f.get("updated"),
    }


def normalize(raw_text):
    """Accept the factory's JSON, raw Jira REST JSON, or markdown/other text.
    Returns a dict, or None for empty input."""
    if raw_text is None or not raw_text.strip():
        return None
    try:
        data = json.loads(raw_text)
    except ValueError:
        data = None
    if isinstance(data, dict):
        if isinstance(data.get("fields"), dict):
            return from_rest(data)
        return data
    keys = find_keys(raw_text)
    return {"key": keys[0] if keys else None, "format": "markdown", "keys_mentioned": keys}


def neighbours(data: dict, own_key: str) -> list:
    """Keys a normalised ticket points at (parent, links, or markdown mentions)."""
    if not isinstance(data, dict):
        return []
    out = []
    if data.get("format") == "markdown" and "keys_mentioned" in data:
        out = list(data.get("keys_mentioned") or [])
    else:
        if data.get("parent_key"):
            out.append(data["parent_key"])
        for l in data.get("links") or []:
            if isinstance(l, dict) and l.get("key"):
                out.append(l["key"])
    res = []
    for k in out:
        if isinstance(k, str) and KEY_RE.match(k) and k != own_key and k not in res:
            res.append(k)
    return res


def render_markdown(d: dict) -> str:
    L = ["# %s: %s" % (d.get("key"), d.get("summary")), "",
         "**Type:** %s" % d.get("issue_type"),
         "**Status:** %s" % d.get("status"),
         "**Parent:** %s" % (d.get("parent_key") or "none"),
         "**Links:** %s" % (", ".join("%s %s" % (l["relation"], l["key"]) for l in d.get("links") or []) or "none"),
         "", "## Description", "", d.get("description") or ""]
    if d.get("acceptance_criteria"):
        L += ["", "## Acceptance criteria", "", d["acceptance_criteria"]]
    return "\n".join(L) + "\n"


def pulled_files(job_path: str) -> dict:
    """{KEY: path} for context/jira/<KEY>.json|.md (json wins)."""
    jdir = os.path.join(job_path, "context", "jira")
    out = {}
    if not os.path.isdir(jdir):
        return out
    for name in sorted(os.listdir(jdir), reverse=True):  # .md first so .json overwrites
        base, ext = os.path.splitext(name)
        if ext in (".json", ".md") and KEY_RE.match(base):
            out[base] = os.path.join(jdir, name)
    return out


def keys_to_pull(job: dict, job_path: str, cfg: dict) -> list:
    jcfg = cfg.get("jira") or {}
    hops = int(jcfg.get("follow_links", 1))
    cap = int(jcfg.get("max_tickets", 8))
    seeds = []
    texts = [job.get("jira_key") or "", job.get("idea") or ""]
    for name in sorted(os.listdir(job_path)):
        if re.match(r"^rework-.*\.md$", name):
            with open(os.path.join(job_path, name)) as f:
                texts.append(f.read())
    for t in texts:
        for k in find_keys(t):
            if k not in seeds:
                seeds.append(k)
    pulled = pulled_files(job_path)
    seen = list(seeds)
    frontier = list(seeds)
    for _ in range(hops):
        nxt = []
        for k in frontier:
            if k not in pulled:
                continue
            with open(pulled[k]) as f:
                data = normalize(f.read())
            for n in neighbours(data, k):
                if n not in seen:
                    seen.append(n)
                    nxt.append(n)
        frontier = nxt
    budget = cap - len(pulled)
    out = []
    for k in seen:
        if k in pulled:
            continue
        if len(out) >= budget:
            break
        out.append(k)
    return out
