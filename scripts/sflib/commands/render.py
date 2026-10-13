from __future__ import annotations

import json
import os
import sys

from .. import SFError, config, jobs, renderers, schema, template


def run(args):
    renderer = renderers.get(args.format)
    cfg = config.try_load() or {}
    tpl = template.load_template(cfg.get("template", "default"))
    job_path = os.path.join(config.jobs_dir(), args.target)
    if os.path.isdir(job_path) and not os.path.isfile(args.target):
        src = os.path.join(job_path, "story.json")
        story = _load(src)
        _check(story)
        out = args.out or os.path.join(job_path, "story" + renderer.EXTENSION)
        jobs.atomic_write(out, renderer.render(story, tpl))
        jobs.update_job(args.target, sets=["title=" + json.dumps(story["title"])])
        print(out)
        return 0
    story = _load(args.target)
    _check(story)
    text = renderer.render(story, tpl)
    if args.out:
        jobs.atomic_write(args.out, text)
        print(args.out)
    else:
        sys.stdout.write(text)
    return 0


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError as e:
        raise SFError("cannot read %s: %s" % (path, e))
    except ValueError as e:
        raise SFError("%s is not valid JSON: %s" % (path, e))


def _check(story):
    errs = schema.validate(story, schema.load_schema("story"))
    if errs:
        raise SFError("story is invalid, run validate: %s" % "; ".join(errs[:3]))


def register(subparsers):
    p = subparsers.add_parser("render", help="render a story.json (job id or path) to markdown")
    p.add_argument("target", metavar="ID_OR_PATH")
    p.add_argument("--format", default="md")
    p.add_argument("--out")
    p.set_defaults(func=run)
