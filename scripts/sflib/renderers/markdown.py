"""Jira-paste-safe markdown: no tables, no checkboxes, no nested lists, no HTML tags."""
from __future__ import annotations

FORMAT = "md"
EXTENSION = ".md"


def _dot(text: str) -> str:
    return text.rstrip().rstrip(".") + "."


def _bullets(items) -> str:
    return "\n".join("- %s" % i for i in items)


def _user_story(v, story):
    return "**As a** %s, **I want** %s, **so that** %s." % (v["as_a"], v["i_want"], v["so_that"])


def _paragraph(v, story):
    return str(v)


def _gwt(v, story):
    blocks = []
    for ac in v:
        label = ac.get("title") or ac.get("kind")
        head = "**%s — %s**" % (ac["id"], label) if label else "**%s**" % ac["id"]
        lines = ["- **Given** %s" % ac["given"], "- **When** %s" % ac["when"], "- **Then** %s" % ac["then"]]
        lines += ["- **And** %s" % a for a in ac.get("and", [])]
        blocks.append(head + "\n\n" + "\n".join(lines))
    return "\n\n".join(blocks)


def _api(v, story):
    out = []
    for a in v:
        line = "- `%s` (%s): %s" % (a["operation"], a["contract"], a["change"])
        if a.get("detail"):
            line += " — %s" % _dot(a["detail"])
        else:
            line += "."
        out.append(line + " Breaking: %s." % a["breaking"])
    return "\n".join(out)


def _deps(v, story):
    if not v:
        return "- None."
    return "\n".join("- %s (%s): %s" % (d["ref"], d["kind"], d["reason"]) for d in v)


def _bug(v, story):
    parts = ["**Observed:** %s" % v["observed"], "**Expected:** %s" % v["expected"],
             "**Steps to reproduce:**\n\n" + "\n".join("%d. %s" % (i, s) for i, s in enumerate(v["steps"], 1))]
    if v.get("environment"):
        parts.append("**Environment:** %s" % v["environment"])
    if v.get("evidence"):
        parts.append("**Evidence:**\n\n" + _bullets(v["evidence"]))
    return "\n\n".join(parts)


def _spike(v, story):
    parts = ["**Question:** %s" % v["question"]]
    if v.get("approach"):
        parts.append("**Approach:**\n\n" + _bullets(v["approach"]))
    parts.append("**Outputs:**\n\n" + _bullets(v["outputs"]))
    return "\n\n".join(parts)


def _epic(v, story):
    parts = ["**Goal:** %s" % v["goal"]]
    if v.get("success_criteria"):
        parts.append("**Success criteria:**\n\n" + _bullets(v["success_criteria"]))
    lines = []
    for c in sorted(v["children"], key=lambda c: c["order"]):
        line = "- %s (%s): %s — %s" % (c["ref"], c["type"], c["title"], _dot(c["summary"]))
        if c.get("depends_on"):
            line += " Depends on: %s." % ", ".join(c["depends_on"])
        lines.append(line)
    parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _refines(v, story):
    return "\n".join("- %s: %s (%s)" % (c["field"], c["summary"], c["reason"]) for c in v["changes"])


def _bullets_style(v, story):
    return _bullets(v)


STYLES = {
    "user-story": _user_story, "paragraph": _paragraph, "bullets": _bullets_style, "gwt": _gwt,
    "api": _api, "deps": _deps, "bug": _bug, "spike": _spike, "epic": _epic, "refines": _refines,
}


def _present(style: str, value) -> bool:
    if value is None:
        return False
    if style == "deps":
        return isinstance(value, list)  # an empty list renders "None."
    if isinstance(value, (list, dict, str)) and not value:
        return False
    return True


def _meta_line(story: dict) -> str:
    parts = ["**Type:** %s" % story["type"].capitalize()]
    jira = story.get("jira") or {}
    if jira.get("key"):
        parts.append("**Jira:** %s%s" % (jira["key"], " (refined)" if story.get("refines") else ""))
    if jira.get("parent_key"):
        parts.append("**Parent:** %s" % jira["parent_key"])
    if jira.get("components"):
        parts.append("**Components:** %s" % ", ".join(jira["components"]))
    return " · ".join(parts)


def render(story: dict, template: dict) -> str:
    blocks = ["# %s" % story["title"], _meta_line(story)]
    extra = story.get("extra") or {}
    sections = [dict(s, _custom=False) for s in template.get("sections", [])]
    sections += [dict(s, _custom=True) for s in template.get("custom_sections", [])]
    for sec in sections:
        if story["type"] not in sec.get("types", []):
            continue
        style = sec["style"]
        value = extra.get(sec["id"]) if sec["_custom"] else story.get(sec.get("field", sec["id"]))
        if not _present(style, value):
            if sec["_custom"] and sec.get("required"):
                blocks.append("## %s\n\n_Missing: %s_" % (sec["heading"], sec["heading"]))
            continue
        body = STYLES[style](value, story)
        blocks.append(("## %s\n\n%s" % (sec["heading"], body)) if sec.get("heading") else body)
    if story.get("open_questions"):
        blocks.append("## Open questions\n\n" + _bullets(story["open_questions"]))
    return "\n\n".join(blocks) + "\n"
