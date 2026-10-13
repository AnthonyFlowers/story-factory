# 0043. epic-status --apply is a pure function of the children

- Date: 2026-10-13
- Status: accepted
- By: step-05 subagent

## Decision

`--apply` computes the epic stage and `gate_reasons` only from the children's stages (ids listed in epic order) and writes through `update_job` (atomic replace). It does nothing while any child is not terminal. Two sessions running it at once write the same values.

## Why

Idempotent without extra locking, as the override requires. A later human `/story approve` on the epic is not preserved: re-running `--apply` recomputes from the children.

## How to undo

Add a lock around the apply.
