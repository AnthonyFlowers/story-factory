# 0054. Reviewers are told to save the review, not reply with it

- Date: 2026-10-13
- Status: accepted
- By: coordinator (smoke test bug 7)

## Decision

The four reviewer agents get a ground rule: the review exists only if saved with Write; never return it as the reply; reply with one line (path and verdict) afterwards.

## Why

In the 2026-10-13 smoke test `reviewer-invest` twice (jobs 004 and 007) ended with the review as a message and no `review-invest.md`. The skill's single re-spawn recovered both, but each cost a minute and a model call.

## How to undo

Delete the bullet from the four reviewer files and the test class.
