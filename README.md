# story-factory

A Claude Code "factory" that writes Jira stories: a writer agent produces a
`story.json`, reviewers check it, and an approver marks it READY or NEEDS-HUMAN.
Nothing is ever written to Jira. This repo holds dummy data only (Jira project
`DEMO`, repo `accounts-api`); config, backlog, jobs and local templates are gitignored.

Python 3.9+ standard library only.

## Setup

```bash
cp factory.config.example.json factory.config.json   # then edit paths
python3 scripts/sf.py settings                       # writes .claude/settings.local.json
git config core.hooksPath scripts/hooks              # pre-commit guard
python3 scripts/sf.py doctor                         # should print OK
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Core commands

```bash
python3 scripts/sf.py new-job --type story --idea "..."   # prints the job id
python3 scripts/sf.py job ID --stage review --round 1
python3 scripts/sf.py list
python3 scripts/sf.py validate path/to/story.json
python3 scripts/sf.py render ID_OR_PATH
```

## Dashboard

```bash
python3 scripts/sf.py dashboard [--port 8765]   # http://127.0.0.1:8765/dashboard.html, loopback only
```

Read-only board of `factory/jobs/` that polls every 2 s. It needs no network. `--jobs-dir DIR` serves a
folder holding `dashboard.html` and `jobs/`; `python3 tests/make_demo_jobs.py DIR` builds one with fake jobs.
