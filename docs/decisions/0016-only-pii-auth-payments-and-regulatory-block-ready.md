# 0016. Only pii, auth, payments and regulatory block READY

- Date: 2026-10-13
- Status: accepted
- By: owner

## Decision

`escalation.always_human` defaults to `pii`, `auth`, `payments` and `regulatory`. Other flags (`audit`, `data-migration`, `breaking-contract`, `third-party`, `product-decision`) are recorded but a story with them can be READY. The brief carries an `## Escalation` section.

## Why

Owner answer to design open question 1.

## How to undo

Edit `escalation.always_human` in `factory.config.json`.
