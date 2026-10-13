# 0060. Lite prompt claims jobs like the Claude skill

- Date: 2026-10-13
- Status: accepted
- By: step-07 subagent

## Decision

The lite prompt runs `sf.py claim` before `resume`, `approve`, `rework` and `render`, stops on BUSY, and mentions `--force` only after the user confirms the holder is dead. `children` relies on the claim that `next-child` makes.

## Why

The coordinator override requires it, and it keeps a Copilot chat and a Claude session from driving one job.

## How to undo

Remove the claim lines in sections 2, 10, 11 and 12 of story-lite.prompt.md.
