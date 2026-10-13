# 0003. Jira is read only

- Date: 2026-10-13
- Status: accepted
- By: owner

## Decision

The factory never writes to Jira. It reads tickets through the owner's `pull-jira-ticket` skill.

## Why

Owner interview 2026-10-13; bank laptop, lowest risk.

## How to undo

Would need a new write path; not planned.
