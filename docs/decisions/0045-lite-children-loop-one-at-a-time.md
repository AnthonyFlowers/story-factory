# 0045. Lite gets a children command that runs one child at a time

- Date: 2026-10-13
- Status: accepted
- By: step-07 subagent

## Decision

`/story-lite children <epic-id>` loops on `sf.py next-child` and runs each child through the resume flow in the same chat. After an epic goes READY the lite prompt only runs `spawn-children` and lists the commands for parallel runs.

## Why

Owner answer 4 makes parallel sessions the main path; the in-chat loop is a sequential convenience that needs no extra mechanism, since `next-child` claims each child.

## How to undo

Delete section 12 and the `children` entry in the argument-hint.
