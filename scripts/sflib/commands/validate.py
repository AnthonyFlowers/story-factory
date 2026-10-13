from __future__ import annotations

import json
import sys

from .. import SFError, schema


def run(args):
    try:
        with open(args.path) as f:
            story = json.load(f)
    except OSError as e:
        raise SFError("cannot read %s: %s" % (args.path, e))
    except ValueError as e:
        print("ERROR : not valid JSON: %s" % e)
        return 1
    errs = schema.validate(story, schema.load_schema("story"))
    if not errs:
        print("OK")
        return 0
    for e in errs:
        print("ERROR %s" % e)
    return 1


def register(subparsers):
    p = subparsers.add_parser("validate", help="validate a story.json against the schema")
    p.add_argument("path")
    p.set_defaults(func=run)
