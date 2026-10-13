---
tags: [project, story-factory, build-step, test]
created: 2026-10-13
---

# Step 08: end-to-end dry run with a dummy LoopBack repo

Part of [story-factory](../../README.md); the architecture is in [design](../design.md). This note stands alone.

## Purpose

Prove the whole factory on the owner's personal Mac, with dummy data only, before it is cloned onto the bank laptop. This step:
- creates a tiny Node/LoopBack-style API repo with an OpenAPI file, as a fixture;
- adds `sf.py check-job`, which verifies a finished job's invariants;
- runs a fixed set of scenarios through `/story` in Claude Code, and records the results.

## Background you need

- Repo `~/Documents/ai/story-factory`. CLI `python3 scripts/sf.py`.
- Claude Code skill: `/story <idea>`, `bug`, `spike`, `epic`, `refine`, `next`, `approve`, `rework`, `resume`, `render`.
- Job folder: `factory/jobs/<id>/` with `job.json`, `brief.md`, `context/jira/`, `story.json`, `story.md`, `round-N/{story.json,checks.md,review-{invest,ac,tech,security}.md}` and `decision.md`.
- Verdict lines:
  - reviews: `VERDICT: PASS|CHANGES` then `FLAGS: …`;
  - decision: `READY|NEEDS-HUMAN` then `FLAGS: …`.
- Terminal stages are `ready` and `needs-human`. Epics pass through `children`.
- The bank escalation floor: any flag, open question, product assumption or leftover CHANGES leads to needs-human.
- Source refs are `<repo-name>:<path>`. The fixture repo's name is `accounts-api`.
- The Jira stub serves DEMO-100 to DEMO-104 from `tests/fixtures/jira/`.
- The Mac memory rule does not bite here: there is no local model, but don't run this while a heavy local job is running.

## Prerequisites

- Steps 01 to 07 are done, and `python3 -m unittest discover -s tests` passes.
- Claude Code is logged in on the Mac. This run uses roughly 60 to 80 agent runs of Claude usage.

## Files to create

```
tests/fixtures/repos/demo-accounts-api/
  package.json                 name demo-accounts-api, scripts {"test":"lb-mocha ...","openapi-spec":"node ./dist/openapi-spec"}, deps listed (@loopback/core, @loopback/rest, @loopback/repository) but NOT installed
  AGENTS.md                    3 lines: LoopBack 4 style dummy service; contract is openapi.json; errors per team-docs
  openapi.json                 OpenAPI 3.0.3, see below
  src/application.ts
  src/controllers/statement.controller.ts
  src/controllers/account.controller.ts
  src/controllers/health.controller.ts
  src/models/statement.model.ts  src/models/account.model.ts
  src/repositories/statement.repository.ts
  src/__tests__/acceptance/statement.controller.acceptance.ts
tests/fixtures/factory.config.e2e.json
scripts/sflib/checkjob.py      (sf.py check-job)
tests/test_checkjob.py
tests/e2e/scenarios.md         (the table below, with a Result column filled in by hand)
```

### `openapi.json` (keep it small and valid JSON)

Paths:
- `GET /health` returns 200 `{status: string}`, operationId `HealthController.ping`.
- `GET /accounts/{accountId}`:
  - 200 Account `{id, nickname, currency, maskedNumber}`;
  - 404 Error;
  - security `bearerAuth`.
- `GET /accounts/{accountId}/statements`:
  - 200 `{items: Statement[]}`, where Statement is `{id, accountId, periodEnd (format: date), closingBalance (string), currency}`;
  - 404 Error;
  - security `bearerAuth`;
  - no query parameters yet.

Components:
- `securitySchemes.bearerAuth` (http bearer);
- `Error` `{error: {code, message}}`.

### Code

The code is plausible LoopBack 4 TypeScript. It does not need to compile.
- `StatementController.find(accountId)` calls `this.accountService.assertOwner(accountId, currentUser)`, then `statementRepository.find({where: {accountId}, order: ['periodEnd DESC']})`. It builds the envelope with `currency: statements[0].currency`. That is the DEMO-102 bug: it throws when the list is empty.
- `HealthController.ping` returns `{status: 'ok'}` and no version.
- Use no real bank names. Comments are minimal.

### `factory.config.e2e.json`

The test config with these changes:
- `repos: [{ "name": "accounts-api", "path": "tests/fixtures/repos/demo-accounts-api", "openapi": ["openapi.json"], "docs": [], "notes": "LoopBack 4 style dummy service" }]`
- `team_docs: [{ "name": "team-docs", "path": "tests/fixtures/team-docs" }]`
- `jira.skill: "pull-jira-ticket-stub"`
- `escalation.extra_terms: ["ledger"]`

### `sf.py check-job ID`

Checks every invariant and prints one `OK <check>` or `FAIL <check>: <detail>` line per check. The last line is `RESULT: PASS` or `RESULT: FAIL`, with exit status 0 or 1.

Checks:
1. `job.json` validates against `schemas/job.schema.json`.
2. The stage is terminal (`ready` or `needs-human`). An epic is also allowed to be `children` only if this flag is passed: `--allow-running`.
3. `story.json` exists and validates. For an epic, also check `children` against the job map.
4. For each round from 1 to `job.round`:
   - `round-N/story.json` and `checks.md` exist;
   - the 4 review files exist;
   - each passes `verdict`.
5. `round` ≤ 2 + the number of `rework-*.md` files.
6. `decision.md` exists and passes `verdict`.
7. If the stage is `ready`:
   - the decision is READY;
   - `gate` prints OK, or `approved_by` is `human`;
   - `story.md` exists and has no table, checkbox or nested-list lines.
8. If the stage is `needs-human`: `decision.md` has a `## For the human` section with at least one numbered item, or `gate_reasons` is non-empty.
9. No file in the job folder is larger than 1 MB.
10. No file outside the job folder changed:
    - `git status --porcelain` must not list tracked files modified by the run;
    - `git -C tests/fixtures/repos/demo-accounts-api` diff is not possible, so compare a SHA-256 manifest instead. `check-job --manifest` writes the manifest before the run; check-job compares against it.

## Scenarios

Run these from the repo root:

```bash
cp tests/fixtures/factory.config.e2e.json factory.config.json
python3 scripts/sf.py settings
python3 scripts/sf.py check-job --manifest
python3 scripts/sf.py dashboard &
claude
```

| # | Command | Hard expectations (must hold) | Soft expectations (record) |
|---|---|---|---|
| S1 | `/story Add the service version from package.json to the GET /health response` | check-job PASS; `api_impact` has `GET /health` with change modify; `sources` cite `accounts-api:src/controllers/health.controller.ts` | stage `ready` |
| S2 | `/story refine DEMO-101` | check-job PASS; `refines.key` is DEMO-101; `context/jira` has DEMO-101, DEMO-100 and DEMO-102; an AC uses `from` and `to` on `GET /accounts/{accountId}/statements`; an AC of kind `security` (another customer's account → 404) | stage `ready` or `needs-human` with reasons, which are recorded |
| S3 | `/story refine DEMO-103` (CSV export with full account number and address) | check-job PASS; stage `needs-human`; `job.flags` contains `pii`; `decision.md` has a question about masking or fields | security review CHANGES in round 1 |
| S4 | `/story bug GET /accounts/{accountId}/statements returns 500 when the account has no statements (DEMO-102)` | check-job PASS; type `bug`; a `regression` AC; `bug.observed` mentions `currency` | stage `ready` |
| S5 | `/story spike Can accounts-api render statement PDFs with an approved library?` | check-job PASS; type `spike`; at least one `deliverable` AC; no `timebox` or estimate words in `story.md` (`grep -iE 'points|hours|days|estimate'` → nothing) | — |
| S6 | `/story epic DEMO-100` | check-job PASS on the epic and on every child; 2 to 7 children; every child `job.json` has `parent` set to the epic id | epic `ready` or `needs-human`; time and number of agent runs |
| S7 | `/story rework <S3 id> "Mask the account number to the last 4 digits and drop the home address"` | check-job PASS; `rework-1.md` exists; a new round folder exists | S3 still `needs-human` (pii stays flagged), with narrower questions |
| S8 | `/story Post a ledger adjustment when a statement is regenerated` | check-job PASS; stage `needs-human`; `gate_reasons` contains `term:ledger` (or a `payments` flag) | — |
| S9 | `/story next` with `factory/backlog.md` copied from the example | the first item becomes `- [x] … → <id>`; check-job PASS | — |
| S10 | `/story approve <S2 id if needs-human>` | stage `ready`, `approved_by` `human`; check-job PASS | — |

### After the scenarios

```bash
for d in factory/jobs/*/; do python3 scripts/sf.py check-job $(basename $d) | tail -1; done   # every line RESULT: PASS
python3 scripts/sf.py check-job --manifest --compare      # → OK manifest unchanged (fixture repo untouched)
git status --porcelain                                    # → nothing under factory/jobs, no fixture changes
python3 scripts/sf.py doctor                              # → OK
lsof -nP -iTCP -sTCP:LISTEN | grep python                 # → only 127.0.0.1:8765
```

Also check:
- Open the dashboard. All jobs are in terminal columns, S3 and S8 stand out, and the epic shows its children.
- **Optional, about 2 minutes:** paste `story.md` from S1 into a scratch Jira Cloud issue on a personal Atlassian site (never the bank's), and record whether headings, bold and lists converted on paste. This settles the unverified paste claim.

## Unit tests (no LLM)

`tests/test_checkjob.py` builds a finished fake job: copy `tests/fixtures/jobs/900-sample`, add 4 PASS reviews, `checks.md` and a READY decision, and set the stage to ready. It asserts `RESULT: PASS`. It then breaks one invariant at a time (missing review, invalid verdict, round 3 with no rework, a ready stage with a NEEDS-HUMAN decision, a table in `story.md`) and asserts the specific `FAIL` line for each.

```bash
python3 -m unittest discover -s tests -v    # all pass
```

## Recording results

Fill in the Result column in `tests/e2e/scenarios.md` with: pass or fail, stage, rounds, flags, and wall time. Commit that file: it holds only dummy data. Report failures of hard expectations as bugs against the step that owns them:
- schema or renderer → 01
- Jira → 02
- agents, checks or gate → 03
- flow → 04
- epics → 05
- dashboard → 06

Do not commit `factory/jobs/`.

## Out of scope

- Running on the work laptop or with any work data.
- Running the dummy repo's code or tests: it is a reading fixture only.
- Prompt tuning beyond fixing hard-expectation failures.
- Copilot lite. Its manual test is in step 07.
