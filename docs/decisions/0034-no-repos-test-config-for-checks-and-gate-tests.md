# 0034. No-repos test config for checks and gate tests

- Date: 2026-10-13
- Status: accepted
- By: coordinator

## Decision

After merging steps 02 and 03, `tests/test_checks.py` and `tests/test_gate.py` use `tests/fixtures/factory.config.norepos.json` (no repos, no team docs). Step 02 had added team docs to the shared test config, which turned the sample's code refs into MISSING and failed 28 tests.

## Why

Keeps each test's assumptions explicit; the shared test config stays as step 02 left it.

## How to undo

Point the tests back at `factory.config.test.json` and give the sample job resolvable refs.
