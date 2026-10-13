# 0007. Story stored as JSON, rendered to markdown first

- Date: 2026-10-13
- Status: accepted
- By: owner

## Decision

Each story is a `story.json` object; renderers convert it, and markdown is the first renderer.

## Why

Owner interview 2026-10-13.

## How to undo

Add renderers; the JSON stays the source of truth.
