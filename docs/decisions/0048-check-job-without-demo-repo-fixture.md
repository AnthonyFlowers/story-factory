# 0048. check-job built without the dummy demo repo fixture

- Date: 2026-10-13
- Status: accepted
- By: coordinator

## Decision

`sf.py check-job` is built and unit tested, but the dummy LoopBack fixture repo, `factory.config.e2e.json` and `tests/e2e/scenarios.md` from step 08 are not built.

## Why

The demo repo only served the deferred dry run (decision 0047).

## How to undo

Build them as described in `docs/steps/08-e2e-dry-run.md`.
