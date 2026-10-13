# 0032. Source checks skipped when nothing is configured

- Date: 2026-10-13
- Status: accepted
- By: step-03 subagent

## Decision

`sf.py checks` reports code and doc refs as `SKIPPED (no repos or team docs configured)` when the config has neither. Once anything is configured, unknown names and missing files are MISSING.

## Why

Lets the gate pass on fixtures without repos; real configs still check every ref.

## How to undo

`scripts/sflib/checks.py`.
