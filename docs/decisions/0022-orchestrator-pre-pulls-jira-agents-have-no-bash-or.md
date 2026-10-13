# 0022. Orchestrator pre-pulls Jira; agents have no Bash or web

- Date: 2026-10-13
- Status: accepted
- By: design

## Decision

The orchestrator pulls tickets into `context/jira/` before agents run. Agents get Read, Grep, Glob and Write only.

## Why

Read-only Jira, and limits what agents can reach on a bank laptop.

## How to undo

Agent `tools` frontmatter.
