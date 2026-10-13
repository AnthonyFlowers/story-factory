# 0046. Prompt test checks the file text only

- Date: 2026-10-13
- Status: accepted
- By: step-07 subagent

## Decision

`tests/test_prompt_file.py` checks frontmatter, referenced agent files, required phrases, known sf.py command names and the absence of URLs. It does not check that `tools` is accepted by VS Code, or that sf.py has `next-child`, `spawn-children` or `epic-status` (step 05 adds them).

## Why

VS Code behaviour is unverified and belongs to the manual test; step 05 commands are absent at this branch point.

## How to undo

Add those checks once step 05 is merged.
