# 0026. One module per sf.py subcommand; parallel worktrees

- Date: 2026-10-13
- Status: accepted
- By: coordinator

## Decision

`sf.py` discovers subcommands in `scripts/sflib/commands/`. Steps 02, 03 and 06 were built in separate git worktrees and merged by the coordinator.

## Why

Parallel subagents never edit the same file.

## How to undo

n/a (build process).
