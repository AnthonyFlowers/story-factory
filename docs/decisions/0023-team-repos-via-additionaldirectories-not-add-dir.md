# 0023. Team repos via additionalDirectories, not --add-dir

- Date: 2026-10-13
- Status: accepted
- By: design

## Decision

Team repos are made readable through `permissions.additionalDirectories` plus Edit deny rules, written by `sf.py settings`.

## Why

`--add-dir` would also load the team repos' own skills and agents.

## How to undo

`sf.py settings`.
