# 0050. doctor warns when Claude Code has not trusted the folder

- Date: 2026-10-13
- Status: accepted
- By: coordinator (smoke test bug 1)

## Decision

`sf.py doctor` prints `WARN: ...` when `~/.claude.json` has no `hasTrustDialogAccepted` for the factory folder. The warning does not change the exit code or the `OK` line. `SF_CLAUDE_JSON` overrides the state file path (tests). A missing or unreadable state file gives no warning.

## Why

The 2026-10-13 smoke test showed Claude Code ignoring `.claude/settings.json` allow rules in an untrusted folder. A headless `/story` run then stopped at the first `sf.py verdict` call with exit 0 and `is_error: false`, leaving the job at stage `review`.

## How to undo

Remove `doctor.warnings` and its call in `commands/doctor.py`.
