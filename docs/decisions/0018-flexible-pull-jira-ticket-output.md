# 0018. Flexible pull-jira-ticket output

- Date: 2026-10-13
- Status: accepted
- By: owner

## Decision

The factory accepts its own normalised JSON, raw Jira REST JSON (`fields.*`) or markdown from `pull-jira-ticket`.

## Why

Owner answer to design open question 3.

## How to undo

Narrow `scripts/sflib/jira.py` `normalize()`.
