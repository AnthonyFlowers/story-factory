# 0049. check-job rules and manifest scope

- Date: 2026-10-13
- Status: accepted
- By: step-08 subagent

## Decision

- The job is checked from `job.json`, not from `git status`. The "nothing changed outside the job" check is the manifest only (`check-job --manifest`, then `--manifest --compare`).
- The manifest hashes every file under every configured repo and team-docs path, except `.git` and `node_modules`. It lives at `<jobs dir>/.manifest.json` and also records the root list, so a config change shows as a difference.
- "Ready" is judged from `job.json` `decision` (READY) plus either `approved_by` human or a clean `gate` result. `/story approve` sets `decision` to READY, so a human-approved job passes.
- An epic at stage ready or needs-human with a READY decision or human approval must have a filled `children` map whose refs match the story, whose children have `parent` set to the epic and are all terminal. An epic at stage `children` (only with `--allow-running`) must also have a filled map, but its children may be running.
- The claim check runs only for terminal jobs. Running jobs legitimately hold a claim.
- Story markdown is checked line by line: a line starting with `|` is a table, `- [ ]` or `- [x]` is a checkbox, an indented list item is a nested list.
- `--manifest` and `--manifest --compare` without a manifest exit 2.

## Why

`.git` changes on a plain `git status` (index refresh), which would give false alarms; `node_modules` is large and not team source. A commit made by mistake would not show in the manifest, but `git status` in the team repo covers that and edits are denied by `sf.py settings`.

## How to undo

Remove `SKIP_DIRS` in `scripts/sflib/checkjob.py` to hash everything, accepting the false alarms.
