"""Parse review and decision files (first line verdict, second line FLAGS)."""
from __future__ import annotations

FLAGS = ["pii", "auth", "payments", "audit", "regulatory", "data-migration",
         "breaking-contract", "third-party", "product-decision"]
REVIEW_VERDICTS = ("PASS", "CHANGES")
DECISIONS = ("READY", "NEEDS-HUMAN")


class Invalid(Exception):
    """The file is not a valid verdict file; str(e) is the reason."""


def parse_text(text: str, kind: str = "any"):
    """Return (verdict, [flags]). kind is 'review', 'decision' or 'any'. Raises Invalid."""
    if not text.strip():
        raise Invalid("empty file")
    lines = text.splitlines()
    first = lines[0].strip()
    verdict = None
    if kind in ("review", "any") and first.startswith("VERDICT:"):
        v = first[len("VERDICT:"):].strip()
        if v in REVIEW_VERDICTS and first == "VERDICT: " + v:
            verdict = v
    if verdict is None and kind in ("decision", "any") and first in DECISIONS:
        verdict = first
    if verdict is None:
        raise Invalid("first line")
    second = lines[1].strip() if len(lines) > 1 else ""
    if not second.startswith("FLAGS:"):
        raise Invalid("flags line")
    raw = second[len("FLAGS:"):].strip()
    if not raw:
        raise Invalid("flags line")
    if raw == "none":
        return verdict, []
    flags = []
    for part in raw.split(","):
        f = part.strip()
        if f not in FLAGS:
            raise Invalid("unknown flag %s" % f)
        if f not in flags:
            flags.append(f)
    return verdict, flags


def parse_file(path: str, kind: str = "any"):
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        raise Invalid("empty file")
    return parse_text(text, kind)
