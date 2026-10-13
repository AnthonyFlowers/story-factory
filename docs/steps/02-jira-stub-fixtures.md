---
tags: [project, story-factory, build-step]
created: 2026-10-13
---

# Step 02: `pull-jira-ticket` stub, Jira fixtures, link following

Part of [story-factory](../../README.md); the architecture is in [design](../design.md). This note stands alone.

## Purpose

The factory reads Jira through a skill that the owner provides, `pull-jira-ticket`. The factory is never allowed to write to Jira. This step:
- fixes the contract the factory depends on;
- ships a stub skill and script that serve dummy fixture tickets;
- adds `sf.py jira-keys`, which tells the orchestrator which tickets to pull next.

## Background you need

- Repo: `~/Documents/ai/story-factory` (created in step 01). It is Python 3.9 stdlib only.
- The CLI is `python3 scripts/sf.py`.
- Config comes from `$STORY_FACTORY_CONFIG` (test config `tests/fixtures/factory.config.test.json`), and jobs from `$STORY_FACTORY_JOBS`.
- A job folder is `<jobs>/<id>/` with `job.json` (keys include `idea` and `jira_key`) and `context/jira/`.
- The orchestrator calls the skill named in `config.jira.skill` and saves its output unchanged:
  - to `context/jira/<KEY>.json` when the output parses as JSON;
  - otherwise to `context/jira/<KEY>.md`.

## Prerequisites

- Step 01 is done: `python3 -m unittest discover -s tests` passes and `scripts/sf.py` exists.

## The contract (write it into README.md under "Jira")

- **Invocation:** `pull-jira-ticket <ISSUE-KEY>`, where the key matches `^[A-Z][A-Z0-9_]+-[0-9]+$`.
- **Read-only.** The factory never calls anything that writes to Jira.
- **Success:** the issue as JSON, preferably in the shape of `schemas/jira-ticket.schema.json`, or as markdown.
- **Failure:** the text starts with `ERROR:`.
- **Factory side:** the factory accepts any JSON. It reads only `key`, `issue_type`, `summary`, `description`, `acceptance_criteria`, `parent_key` and `links[].key` if present. Everything else is passed through to the writer as context.

## Files to create

```
schemas/jira-ticket.schema.json
scripts/jira_stub.py
.claude/skills/pull-jira-ticket-stub/SKILL.md
scripts/sflib/jira.py
tests/fixtures/jira/DEMO-100.json DEMO-101.json DEMO-102.json DEMO-103.json DEMO-104.json
tests/fixtures/team-docs/definition-of-ready.md api-guidelines.md approved-dependencies.md
tests/test_jira.py
```

- Add the `jira-keys` subcommand to `scripts/sf.py`.
- Add `{ "name": "team-docs", "path": "tests/fixtures/team-docs" }` to `team_docs` in `tests/fixtures/factory.config.test.json`.

### `schemas/jira-ticket.schema.json`

- Type object, with `additionalProperties` allowed.
- Required: `key`, `issue_type` and `summary`.
- Properties:
  - `key`, `issue_type`, `summary`, `status`, `description`, `updated`: string
  - `acceptance_criteria`: string or null
  - `labels`, `components`, `fix_versions`: arrays of strings
  - `parent_key`: string or null
  - `links`: array of `{relation, key}`
  - `subtasks`: array of keys

### Fixtures (all dummy, all `DEMO`)

| Key | issue_type | summary | Notes |
|---|---|---|---|
| DEMO-100 | Epic | Statement self-service | goal: customers find and download their own statements; links none |
| DEMO-101 | Story | Statement filter | vague description: "Users want to filter statements. Should work for any dates."; `acceptance_criteria`: "Works for any dates"; parent_key DEMO-100; links relates to DEMO-102 |
| DEMO-102 | Bug | Statements 500 for empty account | description holds a fake stack trace `TypeError: Cannot read properties of undefined (reading 'currency') at StatementController.find`; links none |
| DEMO-103 | Story | Export statements CSV for support | asks for full account number and home address in the CSV (the PII scenario); parent_key DEMO-100 |
| DEMO-104 | Story | Link loop test | links relates to DEMO-101 and DEMO-104 (self), to test cycle handling |

Every fixture has `status`, `labels`, `components`, `fix_versions: []`, `subtasks: []` and `updated: "2026-10-01"`. Use no real names; the reporter is `"Demo User"`.

### `scripts/jira_stub.py`

```
usage: jira_stub.py KEY [--format json|md]
```

- If the key does not match the pattern, print `ERROR: invalid key <KEY>` and exit 64.
- Fixture dir: `$STORY_FACTORY_JIRA_FIXTURES`, else `<root>/tests/fixtures/jira`.
- If the fixture is missing, print `ERROR: <KEY> not found` to stdout and exit 2.
- `json` (the default) prints the fixture, pretty-printed with 2-space indent.
- `md` prints:
  - `# <KEY>: <summary>`
  - lines for `**Type:**`, `**Status:**`, `**Parent:**` and `**Links:**`
  - `## Description`
  - `## Acceptance criteria`, when present
- The script must not import anything that uses the network, and must never open a socket.

### `.claude/skills/pull-jira-ticket-stub/SKILL.md`

```markdown
---
name: pull-jira-ticket-stub
description: TEST DOUBLE for the owner's pull-jira-ticket skill. Returns a dummy DEMO Jira issue from tests/fixtures/jira. Read only.
argument-hint: <ISSUE-KEY> [json|md]
allowed-tools: Bash(python3 scripts/jira_stub.py *)
---

Run `python3 scripts/jira_stub.py $0 --format ${1:-json}` from the repository root
and return its output verbatim, with no commentary. If the output starts with
`ERROR:`, return it unchanged. Never modify any file.
```

If `${1:-json}` is not substituted, use `--format json` when no second argument is given. `$0` and `$1` substitution is documented. Shell-style defaults inside the skill body are not, so prefer the safe form: `Run python3 scripts/jira_stub.py $0, adding --format md only if the second argument is md`.

### `sf.py jira-keys ID`

- **Seeds:** `job.jira_key`, plus every match of `\b[A-Z][A-Z0-9_]+-[0-9]+\b` in `job.idea` and in any `rework-*.md` in the job folder.
- **Links:** for each pulled `context/jira/<KEY>.json`, add its `parent_key` and `links[].key`, up to `config.jira.follow_links` hops (default 1) from the seeds.
- **Output:** the keys that have no `context/jira/<KEY>.json` or `.md` yet, one per line, in discovery order. It never exceeds `config.jira.max_tickets` (default 8) when counting already-pulled keys plus printed keys. Cycles and self-links are ignored.
- **Empty case:** prints nothing and exits 0 when there is nothing to pull.

The orchestrator calls it in a loop:

```
jira-keys → pull each → jira-keys → ... until empty
```

### Team-docs fixtures

These are short and generic:
- `definition-of-ready.md`: five generic DoR bullets.
- `api-guidelines.md`:
  - errors use `{ "error": { "code": "UPPER_SNAKE", "message": "..." } }`;
  - another customer's resource returns 404, not 403;
  - dates are ISO 8601 `format: date`;
  - list endpoints return `{ "items": [...] }`.
- `approved-dependencies.md`: three dummy library names with licences.

## Acceptance tests

```bash
cd ~/Documents/ai/story-factory
python3 -m unittest discover -s tests -v                     # all pass
python3 scripts/jira_stub.py DEMO-101 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["key"], d["parent_key"])'
#   → DEMO-101 DEMO-100
python3 scripts/jira_stub.py DEMO-101 --format md | head -1  # → # DEMO-101: Statement filter
python3 scripts/jira_stub.py DEMO-999; echo "exit=$?"        # → ERROR: DEMO-999 not found / exit=2
python3 scripts/jira_stub.py demo-1; echo "exit=$?"          # → ERROR: invalid key demo-1 / exit=64
export STORY_FACTORY_CONFIG=tests/fixtures/factory.config.test.json STORY_FACTORY_JOBS=$(mktemp -d)
ID=$(python3 scripts/sf.py new-job --type story --mode refine --jira-key DEMO-101 --idea "refine DEMO-101")
python3 scripts/sf.py jira-keys $ID                          # → DEMO-101
python3 scripts/jira_stub.py DEMO-101 > $STORY_FACTORY_JOBS/$ID/context/jira/DEMO-101.json
python3 scripts/sf.py jira-keys $ID                          # → DEMO-100 then DEMO-102 (two lines)
for k in DEMO-100 DEMO-102; do python3 scripts/jira_stub.py $k > $STORY_FACTORY_JOBS/$ID/context/jira/$k.json; done
python3 scripts/sf.py jira-keys $ID                          # → (nothing; 1 hop reached)
python3 scripts/sf.py brief $ID && grep -c 'DEMO-10' $STORY_FACTORY_JOBS/$ID/brief.md   # → 3 or more
```

Manual check in Claude Code, from the repo root, with the test config exported: type `/pull-jira-ticket-stub DEMO-102`. Claude must return the DEMO-102 JSON and edit no file.

Unit tests cover:
- seeds from the idea and from rework files;
- hop limit;
- the max-tickets cap;
- cycle and self-link handling (DEMO-104);
- markdown-format output;
- the error exit codes.

## Out of scope

- The real `pull-jira-ticket` skill, which belongs to the owner.
- Any Jira API client.
- Adapters for raw Jira REST JSON (`fields.*`); this waits for the owner's answer on the output shape.
- Orchestrator logic (step 04).
