# 0042. next-child ordering and claim re-check

- Date: 2026-10-13
- Status: accepted
- By: step-05 subagent

## Decision

`next-child` lists unclaimed, non-terminal children, sorts by (has an unfinished dependency, `order`), and tries `claims.claim` in that order, moving on at BUSY. After winning a claim it re-reads the stage and releases and skips the child if it became terminal meanwhile. The `.claim` file existence is the claimed test. `epic-status` shows `claimed_by=<who>` after the stage only when claimed; RUNNING means any child is not terminal, whether or not it is claimed.

## Why

Dependencies are context, not blockers, so a blocked child is still returned when nothing else is left. The re-check closes the gap where a finished child is listed, then released by `gate --apply`, then claimed again.

## How to undo

Drop the re-check and the sort; plain order.
