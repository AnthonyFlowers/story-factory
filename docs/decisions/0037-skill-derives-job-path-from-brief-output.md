# 0037. Skill derives the job path from brief output

- Date: 2026-10-13
- Status: accepted
- By: step-04 subagent

## Decision

SKILL.md tells the orchestrator that `<job>` is the directory of the path printed by `sf.py brief ID`, and the repo root is `pwd`. No new CLI command was added.

## Why

Shell variables do not persist between Bash calls and the jobs dir can be overridden by `STORY_FACTORY_JOBS`, so the path must come from the CLI. `brief` already prints an absolute path.

## How to undo

Add a `sf.py path ID` command and use it in the skill.
