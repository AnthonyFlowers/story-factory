# 0036. Claim file format and release points

- Date: 2026-10-13
- Status: accepted
- By: step-04 subagent

## Decision

`<job>/.claim` holds JSON `{who, pid, time}`, created with O_CREAT|O_EXCL by `scripts/sflib/claims.py`. `new-job` claims for its creator. `gate --apply` and `escalate` release (both outcomes are terminal). The skill releases explicitly after `approve` and `render`, and for `resume` of a terminal job. `release` on an unclaimed job is a no-op.

## Why

The override left the file format and who releases when the stage is changed by the skill (not by gate or escalate) open. Releasing in the skill keeps the CLI commands that only set a stage free of side effects.

## How to undo

Delete `claims.py`, `commands/claim.py` and the three one-line calls in `new_job.py`, `gate.py`, `escalate.py`.
