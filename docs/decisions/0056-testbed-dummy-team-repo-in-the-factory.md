# 0056. Testbed dummy team repo is versioned in the factory

- Date: 2026-10-13
- Status: accepted
- By: owner (via coordinator)

## Decision

The dummy team repo used in the 2026-10-13 smoke test is kept as plain files in `testbed/team-repo/` (no `.git`). `sf.py testbed PATH` copies it to PATH, runs `git init`, makes one commit and prints the `factory.config.json` snippet. Nothing references `testbed/` by default: repos come only from `factory.config.json`, and a test checks the example and test configs do not name it.

## Why

The owner wants the generated repo for future smoke tests. A nested `.git` would make it a submodule-like blob; plain files plus a generator keep the factory repo simple and the team repo disposable.

## How to undo

Delete `testbed/`, `commands/testbed.py`, `tests/test_testbed.py` and the Testbed section of TESTING.md.
