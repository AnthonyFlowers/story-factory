---
name: pull-jira-ticket-stub
description: TEST DOUBLE for the owner's pull-jira-ticket skill. Returns a dummy DEMO Jira issue from tests/fixtures/jira. Read only.
argument-hint: <ISSUE-KEY> [json|md]
allowed-tools: Bash(python3 scripts/jira_stub.py *)
---

Run `python3 scripts/jira_stub.py $0` from the repository root, adding `--format md`
only if the second argument (`$1`) is `md`. Return its output verbatim, with no
commentary. If the output starts with `ERROR:`, return it unchanged. Never modify any file.
