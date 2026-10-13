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

## Dashboard

```bash
python3 scripts/sf.py dashboard [--port 8765]   # http://127.0.0.1:8765/dashboard.html, loopback only
```

Read-only board of `factory/jobs/` that polls every 2 s. It needs no network. `--jobs-dir DIR` serves a
folder holding `dashboard.html` and `jobs/`; `python3 tests/make_demo_jobs.py DIR` builds one with fake jobs.

## Agents, checks and gate

Six Claude Code subagents live in `.claude/agents/`: `story-writer`, `reviewer-invest`, `reviewer-ac`, `reviewer-tech`, `reviewer-security` and `story-approver`. Each is given `Job folder: <abs job dir>. Repo root: <abs factory root>.`, reads files only, and writes exactly one file. They have no Bash, Edit, web or Agent tools.

```bash
python3 scripts/sf.py checks ID --round N     # snapshot story.json to round-N/, write round-N/checks.md
python3 scripts/sf.py verdict FILE            # parse a review or decision: "PASS flags=pii,auth" or "INVALID <reason>"
python3 scripts/sf.py gate ID [--apply]       # bank escalation floor: "OK" or "HUMAN: <reasons>"
python3 scripts/sf.py escalate ID --why TEXT  # write a NEEDS-HUMAN decision.md and set the stage
```

Only the flags in `escalation.always_human` (default `pii`, `auth`, `payments`, `regulatory`) force NEEDS-HUMAN. When no repos or team docs are configured, source and API existence checks are SKIPPED.

## Docs

- [docs/design.md](docs/design.md): architecture, schemas, state machine, agents, escalation rules.
- [docs/steps/](docs/steps/): the build steps 01 to 08, each a standalone spec.
- [docs/decisions/](docs/decisions/README.md): one file per decision, numbered, with why and how to undo.

## Commands

The `/story` skill (`.claude/skills/story/SKILL.md`) is the orchestrator: start `claude` in this repo and type `/story <idea>`, `/story bug <text>`, `/story spike <q>`, `/story refine KEY`, `/story epic <idea|KEY>`, `/story next`, `/story approve <id>`, `/story rework <id> <note>`, `/story resume <id>` or `/story render <id>`. It only runs `sf.py`, the Jira skill and the agents.

```bash
python3 scripts/sf.py claim ID [--force] [--who TEXT]   # CLAIMED ID, or BUSY ID <who> <time> and exit 3
python3 scripts/sf.py release ID
python3 scripts/sf.py backlog claim                      # LINE<TAB>TYPE<TAB>TEXT of the first "- [ ]" item, or nothing
python3 scripts/sf.py backlog done LINE ID
```

`new-job` claims the job it creates, so two sessions never drive one job; `gate --apply` and `escalate` release it. `/story resume`, `approve`, `rework` and `render` claim first and stop on BUSY. The backlog is `factory/backlog.md` (gitignored, copied from `factory/backlog.example.md` on first use) and is locked with `flock`.

## Epics

`/story epic <idea|KEY>` drafts and reviews an epic breakdown like any other job. When it is READY (or after `/story approve`), the epic run creates one child job per child, prints a launch block and stops. Open several Claude Code sessions in this repo and run `/story children <epic-id>` in each: every session claims one child at a time with `next-child` until none are left. Or run a single child with `/story resume <child-id>`.

```bash
python3 scripts/sf.py spawn-children EPIC_ID        # REF<TAB>JOB_ID per child, in dependency order; idempotent; leaves children unclaimed
python3 scripts/sf.py next-child EPIC_ID [--who T]  # claim and print the next child id, or print nothing when none is left
python3 scripts/sf.py epic-status EPIC_ID [--apply] # one line per child, then ALL-DONE ready=N needs-human=M, or RUNNING
```

`spawn-children` needs the epic at stage `ready`, or `needs-human` after `/story approve`; it rejects unknown `depends_on` refs and cycles. `next-child` prefers children whose siblings are all done, then the lowest `order`. `epic-status --apply` sets the epic to `ready`, or to `needs-human` with `gate_reasons: ["children-need-human:<ids>"]`, once every child is terminal; it is safe to run from several sessions. A child's `brief.md` gets a `## Parent epic` section.

## Copilot lite

`.github/prompts/story-lite.prompt.md` is a fallback for VS Code GitHub Copilot (agent mode). Open the repo folder and type `/story-lite <idea>` (also `bug`, `spike`, `epic`, `refine`, `children`, `resume`, `approve`, `rework`, `render`). It plays the writer, the four reviewers (security, tech, ac, invest) and the approver in one chat, then runs `sf.py gate --apply`. The job folder is the same as the Claude `/story` skill's, with `"harness": "copilot-lite"` in `job.json`. It never writes to Jira; when a ticket is missing it stops and asks you to save your Jira skill output under `context/jira/` and run `/story-lite resume <id>`. Epic children are created with `spawn-children`; run them in separate chats or Claude sessions.

Manual test (not yet run): copy `tests/fixtures/factory.config.test.json` to `factory.config.json`, run `/story-lite bug DEMO-102 statements 500 for empty accounts`, save `python3 scripts/jira_stub.py DEMO-102` output to the path it asks for, then `/story-lite resume <id>`. Record here: whether `tools: [...]` was accepted, whether Copilot asked for terminal approval on each `sf.py` call, and the model used.
