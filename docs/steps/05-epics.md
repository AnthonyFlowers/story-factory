---
tags: [project, story-factory, build-step]
created: 2026-10-13
---

# Step 05: epic breakdown and children

Part of [story-factory](../../README.md); the architecture is in [design](../design.md). This note stands alone.

## Purpose

Support `/story epic <idea|KEY>`:
1. The writer drafts an epic `story.json` with a child list.
2. The four reviewers check the breakdown.
3. The approver rules on it.
4. On READY (or after `/story approve`), each child becomes its own job and runs the full story loop, one after another.
5. The epic is ready when every child is ready; otherwise it is needs-human.

## Background you need

- Repo `~/Documents/ai/story-factory`; CLI `python3 scripts/sf.py`; the orchestrator skill is `.claude/skills/story/SKILL.md`.
- An epic is `story.json` with `"type": "epic"` and `epic: {goal, success_criteria[], children[]}`. Each child is `{ref: "C1", type: story|bug|spike, title, summary, order, depends_on: ["C2"]}`.
- The agents already have epic branches in their bodies (step 03):
  - the writer emits 2 to 7 children;
  - invest checks independence and overlap;
  - ac checks success criteria;
  - tech checks order;
  - security checks risk spread.
- `job.json` has `parent` (string or null) and `children` (an object mapping a ref to a job id). Stage `children` exists in the job schema.
- Jobs are created with `sf.py new-job --type T [--parent ID] [--jira-key K] --idea TEXT`.

## Prerequisites

- Steps 01 to 04 are done, the unit tests pass, and a single `/story` run has worked once.

## Files to create or change

```
scripts/sflib/epics.py
sf.py: subcommands spawn-children, epic-status
.claude/skills/story/SKILL.md: add "## Epic" section (replace the one-line placeholder)
tests/test_epics.py
tests/fixtures/jobs/910-epic-sample/ (job.json type epic stage approve; story.json = the epic example; decision.md READY)
```

## Interfaces

### `sf.py spawn-children EPIC_ID`

Requirements and checks:
- The epic's `job.json` stage must be `ready`, or `needs-human` with `approved_by: human` already applied by `/story approve`.
- `story.json` must be `type: epic`.
- Every `depends_on` ref must exist among the children, with no cycles. If there is a cycle, print `ERROR: dependency cycle C1 -> C3 -> C1` and exit 1.

For each child in topological order, with ties broken by `order`, it runs `new-job` with:
- `--type <child.type>`
- `--parent EPIC_ID`
- `--idea` set to the text below
- `--jira-key` set to the epic's `jira.key` only when the epic came from a key. This makes the pull loop fetch the epic ticket for the child's context.

The `--idea` text:

```
<child.title>. <child.summary>
(Child <ref> of epic <EPIC_ID>: <epic title>. Epic story: <abs path to epic story.json>. Depends on: <refs → titles or none>.)
```

Then:
- it sets the epic's `children` to `{ref: job_id}` and its `stage` to `children`;
- it prints one `ref<TAB>job_id` line per child.

It is idempotent: if `children` is already filled, it prints the existing map and creates nothing.

### `sf.py epic-status EPIC_ID [--apply]`

- Prints one line per child: `<ref>  <job_id>  <stage>`.
- Then prints `ALL-DONE ready=<n> needs-human=<m>` or `RUNNING`.
- With `--apply` and all children terminal (`ready` or `needs-human`), it sets the epic's `stage`:
  - `ready` when m == 0;
  - otherwise `needs-human`, with `gate_reasons: ["children-need-human:<ids>"]`.

### `brief.md` for a child

`sf.py brief` must detect `parent` and add a `## Parent epic` section. It holds:
- the epic `story.json` path;
- the epic goal;
- this child's ref and `depends_on`;
- the sibling titles, which the writer must not overlap.

## `SKILL.md` "## Epic" section

1. `/story epic <idea|KEY>` runs **New job** with `--type epic`. The loop is the same: draft, review rounds, approve, gate.
2. After `gate --apply`:
   - `ready` → run `sf.py spawn-children ID`.
   - `needs-human` → stop and report. The owner can `/story approve ID`, after which the orchestrator runs `spawn-children` and continues, or `/story rework ID <note>`.
3. **Children loop:**
   - For each `ref<TAB>job_id` line, in order, run the child through the single-job flow, starting at the Jira pull loop, then Draft.
   - Run one child at a time. Children are never parallel; this keeps cost and context bounded.
   - A child's NEEDS-HUMAN does not stop its siblings.
   - After each child, report one line: `epic 007: C2 → 009-... needs-human (2 of 3 done)`.
4. Run `sf.py epic-status ID --apply` and report the final epic stage plus each child's result.
5. **`/story resume <epic-id>`** with stage `children`:
   - run `sf.py epic-status ID`;
   - resume every child that is not terminal, in `children` order, as `/story resume <child>`;
   - then `epic-status --apply`.
6. **Context discipline.** After each child finishes, keep only its one-line result in mind. The child's files hold everything else.

## Acceptance tests

```bash
cd ~/Documents/ai/story-factory
python3 -m unittest discover -s tests -v      # all pass
export STORY_FACTORY_CONFIG=tests/fixtures/factory.config.test.json STORY_FACTORY_JOBS=$(mktemp -d)
cp -R tests/fixtures/jobs/910-epic-sample $STORY_FACTORY_JOBS/
python3 scripts/sf.py job 910-epic-sample --stage ready --decision READY --approved-by agent >/dev/null
python3 scripts/sf.py spawn-children 910-epic-sample
#   → C1<TAB>911-filter-statements-date-range
#     C2<TAB>912-server-side-statement-pdfs
#     C3<TAB>913-download-statement-pdf        (C3 after C2: depends_on)
python3 scripts/sf.py spawn-children 910-epic-sample   # → same three lines, no new folders
ls $STORY_FACTORY_JOBS | wc -l                         # → 4
grep -c '## Parent epic' $STORY_FACTORY_JOBS/911-*/brief.md   # → 1
python3 scripts/sf.py epic-status 910-epic-sample      # → three lines with "intake", then RUNNING
for j in 911 912 913; do python3 scripts/sf.py job $(ls $STORY_FACTORY_JOBS | grep ^$j) --stage ready >/dev/null; done
python3 scripts/sf.py epic-status 910-epic-sample --apply   # → ... ALL-DONE ready=3 needs-human=0 ; epic stage ready
```

Unit tests also cover:
- cycle detection, with an `ERROR` exit;
- an unknown `depends_on` ref;
- the epic not being ready: `ERROR: epic 910-... is in stage approve`;
- a mixed result giving `needs-human` with a `children-need-human:` reason.

**Manual** (Claude Code on the Mac, dummy data; about 24 agent runs): `/story epic DEMO-100`.

Expected:
- The epic job ends with stage `ready` or `needs-human`.
- `job.json.children` has 2 to 7 entries.
- Every child folder has `story.json` (valid), at least one round folder and `decision.md`.
- `sf.py list` shows every child with `parent` set. Check `cat */job.json | grep parent`.

## Out of scope

- Running children in parallel sessions. The owner may do it by hand with `/story resume <child>` in several sessions; the flow does not depend on it.
- Re-planning the epic from child results.
- Writing epic or child links to Jira.
