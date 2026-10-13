#!/usr/bin/env python3
"""TEST DOUBLE for pull-jira-ticket. Serves dummy DEMO tickets from fixtures. Read only, no network."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sflib import config, jira  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jira_stub.py")
    ap.add_argument("key")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    args = ap.parse_args(argv)
    if not jira.KEY_RE.match(args.key):
        print("ERROR: invalid key %s" % args.key)
        return 64
    d = os.environ.get("STORY_FACTORY_JIRA_FIXTURES") or os.path.join(config.root(), "tests", "fixtures", "jira")
    jp, mp = os.path.join(d, args.key + ".json"), os.path.join(d, args.key + ".md")
    if os.path.isfile(jp):
        with open(jp) as f:
            text = f.read()
        data = jira.normalize(text)
        if args.format == "md":
            sys.stdout.write(jira.render_markdown(data))
        elif isinstance(data, dict) and isinstance(json.loads(text).get("fields"), dict):
            sys.stdout.write(text if text.endswith("\n") else text + "\n")
        else:
            print(json.dumps(data, indent=2))
        return 0
    if os.path.isfile(mp):
        with open(mp) as f:
            sys.stdout.write(f.read())
        return 0
    print("ERROR: %s not found" % args.key)
    return 2


if __name__ == "__main__":
    sys.exit(main())
