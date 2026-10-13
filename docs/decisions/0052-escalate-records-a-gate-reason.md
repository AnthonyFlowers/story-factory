# 0052. escalate records a gate reason

- Date: 2026-10-13
- Status: accepted
- By: coordinator (smoke test bug 6)

## Decision

`sf.py escalate ID --why TEXT` also sets `gate_reasons` to `["escalated: <TEXT, whitespace collapsed, first 120 characters>"]`.

## Why

A blocked writer (job 002 in the smoke test) ended `needs-human` with `gate_reasons` and `flags` empty, so `sf.py job` and the dashboard gave no reason; the only explanation was in decision.md.

## How to undo

Drop the `sets=` argument in `commands/escalate.py`.
