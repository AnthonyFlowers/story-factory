# 0038. Backlog keeps the type prefix on checked lines

- Date: 2026-10-13
- Status: accepted
- By: step-04 subagent

## Decision

`backlog claim` rewrites `- [ ] bug: X` to `- [x] bug: X → claimed` (prefix kept) and prints the type and the text without the prefix. `backlog done N ID` replaces `→ claimed` and fails if line N is not claimed. `STORY_FACTORY_BACKLOG` overrides the file path (used by tests).

## Why

Keeping the prefix preserves the owner's original line and shows the job type later. Failing on an unclaimed line stops a wrong line number from overwriting history.

## How to undo

Edit `scripts/sflib/backlog.py`.
