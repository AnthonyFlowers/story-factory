# 0053. Skill runs one plain command per Bash call; sf.py human

- Date: 2026-10-13
- Status: accepted
- By: coordinator (smoke test bug 2)

## Decision

SKILL.md tells the orchestrator to make one plain `python3 scripts/sf.py ...` call per Bash call (no variables, `&&`, `;`, pipes, loops, redirects, `sed`). The `CHILD=$(...)` step now reads the printed id. New `sf.py human ID` prints the `## For the human` section of `decision.md`, replacing the `sed -n` the orchestrator improvised in every run.

## Why

In the 2026-10-13 smoke test the orchestrator's compound commands and `sed` calls were denied in headless mode because they do not match `Bash(python3 scripts/sf.py *)`; each would be an approval prompt interactively.

## How to undo

Delete `commands/human.py`, `tests/test_human.py` and the added SKILL.md bullet.
