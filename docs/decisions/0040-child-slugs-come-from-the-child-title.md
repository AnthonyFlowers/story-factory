# 0040. Child slugs come from the child title

- Date: 2026-10-13
- Status: accepted
- By: step-05 subagent

## Decision

`jobs.new_job` takes an optional `slug_text`; `spawn-children` passes the child title, so the job id is `913-download-statement-pdf` even though the idea text continues with the summary. `slugify` itself is unchanged.

## Why

The idea starts with the title but runs on into the summary, and `slugify` keeps the first four words, so the slug would have been `download-statement-pdf-add`. The step note's expected ids use the title only.

## How to undo

Drop the `slug_text` argument; ids then include summary words.
