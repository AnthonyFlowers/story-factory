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

## Agents, checks and gate

Six Claude Code subagents live in `.claude/agents/`: `story-writer`, `reviewer-invest`, `reviewer-ac`, `reviewer-tech`, `reviewer-security` and `story-approver`. Each is given `Job folder: <abs job dir>. Repo root: <abs factory root>.`, reads files only, and writes exactly one file. They have no Bash, Edit, web or Agent tools.

```bash
python3 scripts/sf.py checks ID --round N     # snapshot story.json to round-N/, write round-N/checks.md
python3 scripts/sf.py verdict FILE            # parse a review or decision: "PASS flags=pii,auth" or "INVALID <reason>"
python3 scripts/sf.py gate ID [--apply]       # bank escalation floor: "OK" or "HUMAN: <reasons>"
python3 scripts/sf.py escalate ID --why TEXT  # write a NEEDS-HUMAN decision.md and set the stage
```

Only the flags in `escalation.always_human` (default `pii`, `auth`, `payments`, `regulatory`) force NEEDS-HUMAN. When no repos or team docs are configured, source and API existence checks are SKIPPED.
