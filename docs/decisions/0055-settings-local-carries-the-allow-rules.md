# 0055. settings.local.json carries the allow rules and the Jira skill

- Date: 2026-10-13
- Status: accepted
- By: coordinator (smoke test bugs 1 and 5)

## Decision

`sf.py settings` writes `permissions.allow` into `.claude/settings.local.json`: `Bash(python3 scripts/sf.py *)`, `Bash(python3 scripts/jira_stub.py *)` and `Skill(<jira.skill>)`. The same `sf.py` rules stay in the shared `.claude/settings.json`.

## Why

In the smoke test Claude Code ignored the allow rules in `.claude/settings.json` (`this workspace has not been trusted`) but honoured `settings.local.json`. With the rules only in the shared file, headless runs stalled at `sf.py verdict`, and the Skill tool call to the Jira skill returned `Execute skill: ...` as an error, which the orchestrator escalated as a failed pull. With the local rules, a run with no `--allowedTools` flag pulled the ticket and ran to completion of intake. `doctor` still warns about trust (decision 0050), since other behaviour may depend on it.

## How to undo

Remove the `allow` key from `settings.build`.
