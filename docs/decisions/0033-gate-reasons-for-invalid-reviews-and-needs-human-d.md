# 0033. Gate reasons for invalid reviews and NEEDS-HUMAN decisions

- Date: 2026-10-13
- Status: accepted
- By: step-03 subagent

## Decision

`sf.py gate` adds `review-invalid:<lens>` for a missing or invalid final-round review and `decision-needs-human` when the approver said NEEDS-HUMAN, so the gate never prints OK for a NEEDS-HUMAN decision. It recomputes everything from story.json and the highest round folder.

## Why

Makes the gate's output always agree with the final stage.

## How to undo

`scripts/sflib/gate.py`.
