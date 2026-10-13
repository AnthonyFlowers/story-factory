# 0028. Job number claim marker

- Date: 2026-10-13
- Status: accepted
- By: step-01 subagent

## Decision

`new-job` claims job numbers with a hidden `.n-NNN` marker directory in the jobs dir.

## Why

Stops two concurrent sessions taking the same number with different slugs.

## How to undo

`scripts/sflib/jobs.py`.
