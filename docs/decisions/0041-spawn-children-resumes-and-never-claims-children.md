# 0041. spawn-children uses the library, resumes partial runs, rewrites the child brief

- Date: 2026-10-13
- Status: accepted
- By: step-05 subagent

## Decision

`spawn-children` calls `jobs.new_job` directly (not the `new-job` command), so a child is never claimed and there is nothing to release. It saves the epic's `children` map after every child and only sets stage `children` at the end; a re-run after an interruption creates only the missing children. It rewrites each child's `brief.md` after the map is saved, so the `## Parent epic` section knows the child's ref. Idempotence is checked before the stage check, because the stage is `children` afterwards. The epic's claim is released after a real spawn.

## Why

The override says to release each child claim right after creation; never taking it is the same result without a window where a session could see a held child. Saving per child avoids duplicate jobs after a crash. The brief is written inside `new_job` before the parent map has the child.

## How to undo

Revert to one map write at the end; accept duplicates after a crash.
