# 0017. No extra Jira fields in story.json

- Date: 2026-10-13
- Status: accepted
- By: owner

## Decision

story.json carries labels, components, parent and links only.

## Why

Owner answer to design open question 2.

## How to undo

Add fields to `schemas/story.schema.json` and the renderer.
