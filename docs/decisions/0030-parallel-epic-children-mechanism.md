# 0030. Parallel epic children mechanism

- Date: 2026-10-13
- Status: accepted
- By: coordinator

## Decision

`spawn-children` creates child jobs and releases their claims; `sf.py next-child <epic>` claims the next child atomically; `/story children <epic>` loops in as many sessions as wanted. The epic run prints a launch block and stops.

## Why

Owner answer 4 (parallel sessions) without collisions.

## How to undo

Step 05 code; fall back to `/story resume <child>`.
