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

## Jira

The factory reads Jira through the owner's `pull-jira-ticket` skill (named in
`config.jira.skill`). It never writes to Jira. `pull-jira-ticket-stub` is a test
double that serves dummy `DEMO` tickets from `tests/fixtures/jira`.

- **Invocation:** `pull-jira-ticket <ISSUE-KEY>`, key matching `^[A-Z][A-Z0-9_]+-[0-9]+$`.
- **Read-only:** the factory never calls anything that writes to Jira.
- **Success:** the issue as JSON or markdown. All three shapes are accepted:
  the factory's own JSON (`schemas/jira-ticket.schema.json`), raw Jira REST JSON
  (`{"key": ..., "fields": {...}}`, ADF descriptions flattened), or markdown.
- **Failure:** the text starts with `ERROR:`.
- **Saved as:** `context/jira/<KEY>.json` when the output parses as JSON, else `.md`.
- **Factory side:** `sflib.jira.normalize()` maps the three shapes. The factory reads
  `key`, `issue_type`, `summary`, `description`, `acceptance_criteria`, `parent_key` and
  `links[].key`; the rest is passed through to the writer as context.

```bash
python3 scripts/jira_stub.py DEMO-101 [--format json|md]
python3 scripts/sf.py jira-keys ID    # keys still to pull; loop: jira-keys, pull each, repeat until empty
```

`jira-keys` seeds from `job.jira_key` and keys in the idea and `rework-*.md`, follows
parent and links up to `jira.follow_links` hops, and never exceeds `jira.max_tickets`.
