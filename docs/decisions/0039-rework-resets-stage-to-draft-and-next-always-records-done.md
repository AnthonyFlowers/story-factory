# 0039. Rework resets stage to draft; next always records done

- Date: 2026-10-13
- Status: accepted
- By: step-04 subagent

## Decision

`/story rework` sets `--stage draft` along with the other resets, so a crash mid-rework resumes at the writer. `/story next` runs `backlog done` even when the job stops early (escalated or needs-human), so the backlog line always names the job.

## Why

The step note's reset list left the stage unchanged, which would leave a ready job looking finished while a rework is running. An unrecorded claimed line would be lost work.

## How to undo

Edit sections 10 and 12 of SKILL.md.
