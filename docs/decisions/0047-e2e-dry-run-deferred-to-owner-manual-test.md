# 0047. E2E dry run deferred to the owner's manual test

- Date: 2026-10-13
- Status: accepted
- By: owner

## Decision

No automated end-to-end dry run is built or run. The owner tests the factory on the work laptop with real Jira (through their own `pull-jira-ticket` skill) and real team repos, following `docs/TESTING.md`.

## Why

The owner prefers to test with real tickets and repos.

## How to undo

Run the scenarios in `docs/steps/08-e2e-dry-run.md`.
