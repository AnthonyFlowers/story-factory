# 0021. Deterministic gate after the approver

- Date: 2026-10-13
- Status: accepted
- By: design

## Decision

A Python stdlib `sf.py gate` runs after the approver and can only make the outcome stricter.

## Why

An LLM approver alone can miss a bank flag.

## How to undo

Remove the `gate --apply` call in the skill.
