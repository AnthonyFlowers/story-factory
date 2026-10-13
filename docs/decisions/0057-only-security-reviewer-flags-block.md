# 0057. Only the security reviewer's flags block READY

- Date: 2026-10-13
- Status: accepted
- By: owner (smoke test bug 4)

## Decision

1. NEEDS-HUMAN for sensitivity is forced only by flags in `escalation.always_human` (default `pii`, `auth`, `payments`, `regulatory`) that appear on the `FLAGS:` line of the final round's `review-security.md`. `sf.py gate` reads that line deterministically.
2. The writer's `risk_flags` stay in `story.json` as hints for the security reviewer. They, other reviewers' flags and the decision's flags are still recorded in `job.json` `flags`, but never block.
3. Open questions and assumptions (including `kind: product`) no longer block. The markdown renderer shows them as "Open questions for the team" and "Assumptions". Template item DOR5 is now a `review` item ("open questions, if any, are written as answerable questions") instead of the auto "no open questions" check.
4. Still forced to NEEDS-HUMAN: a remaining CHANGES verdict after the last round, a missing or invalid review (a missing `FLAGS:` line included, so a security review without it defaults to a human), a missing or invalid decision, a schema error, a MISSING source, an `extra_terms` word, and the approver's own NEEDS-HUMAN.

Supersedes the blocking part of 0016 (which flags block); the flag vocabulary and `always_human` setting are unchanged.

## Why

In the Claude smoke test 0 of 7 jobs reached READY, because the writer flags pii, auth, payments or regulatory on almost any bank story and open questions also gated. The owner chose to put the sensitivity judgement with the one reviewer whose lens it is.

## How to undo

In `gate.py` collect blocking flags from all sources again instead of `sec_flags`, and re-add the `open-questions` and `product-assumption` reasons.
