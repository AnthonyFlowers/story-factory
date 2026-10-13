# 0029. claimed_by and per-job claims

- Date: 2026-10-13
- Status: accepted
- By: coordinator

## Decision

`job.json` gains `claimed_by`, and per-job `.claim` files are added in step 04.

## Why

Needed for parallel epic children (owner answer 4).

## How to undo

Drop the field and the claim command.
