# 0027. Raw REST ticket mapping

- Date: 2026-10-13
- Status: accepted
- By: coordinator

## Decision

For raw REST tickets, `acceptance_criteria` is null and the parent comes only from `fields.parent`; custom fields are not guessed.

## Why

Jira has no standard AC field, and epic-link custom fields differ per site.

## How to undo

Add a config field mapping in `scripts/sflib/jira.py`.
