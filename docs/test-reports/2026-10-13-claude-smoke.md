# Claude Code smoke test, 2026-10-13

**Verdict: PASS WITH BUGS.** The pipeline runs end to end headless under Claude Code, subagents do read the team repo, escalation and the manifest guard work, and `check-job` passes on all 7 jobs. But no job reached READY (all 7 ended NEEDS-HUMAN), and a headless run stalls silently if the workspace is not trusted or if the orchestrator issues a compound shell command.

## Environment

- Claude Code 2.1.296, macOS (Darwin 25.5), factory main at d82885f.
- Models: session/orchestrator claude-opus-5-5; `story-writer` pins opus; reviewers and approver ran on claude-sonnet-5-5 (`modelUsage` showed both). No `--model` override.
- Run as `claude -p "/story ..." --output-format json --permission-mode acceptEdits --allowedTools "Bash(python3 scripts/sf.py *)" "Bash(python3 scripts/jira_stub.py *)"` (the first run had no `--allowedTools`; see bug 1).
- Smoke clone: `/Users/ant/Documents/ai/story-factory-smoke`. Dummy team repo (accounts/transfers LoopBack API, 7 files): `/Users/ant/Documents/ai/story-factory-smoke-team`. Config: stub Jira skill, project DEMO, `escalation.always_human` default. An untracked fixture `tests/fixtures/jira/DEMO-110.json` (transfers ticket) was added to the clone because every shipped fixture is about statements.
- `sf.py settings`, `doctor` (OK) and `check-job --manifest` (7 files) all worked.

## Results

Wall times are from the harness. Cost is reported by Claude Code.

| # | Command | Wall | Job, final stage | Gate | Result |
|---|---|---|---|---|---|
| 1 | `/story Let customers see the status of a pending transfer` | 153 s, then stalled (bug 1); finished by `/story resume` after `claim --force` (232 s) | 001, needs-human, r2, 1 revision | HUMAN: flags pii/auth/payments/regulatory, product assumptions, ac CHANGES left, approver NEEDS-HUMAN | check-job PASS. Story is good (below). |
| 2 | additionalDirectories | n/a | 001 and all others | n/a | YES, subagents read the repo (below) |
| 3 | `/story Show the customer's full SSN on the profile page` | 375 s | 003, needs-human, r2 | HUMAN: pii/auth/regulatory flags, open questions | check-job PASS. Narrowed to `GET /customers/{id}/ssn` with re-auth, no-cache, rate limit, audit, 13 ACs; decision.md ends with numbered questions. |
| 4a | `/story refine DEMO-101` | 124 s | 002, needs-human, r0 | gate_reasons empty (bug 6) | Writer blocked: shipped fixture is about `GET /statements`, which the dummy repo lacks. Correct behaviour, no review round. |
| 4b | `/story refine DEMO-110` (added fixture) | 399 s | 004, needs-human, r2 | HUMAN (flags, ac CHANGES left) | check-job PASS. "Changes from the original ticket" section present; proposed new `GET /accounts/{id}/transfers`. |
| 5a | `/story epic Customers can schedule a transfer ... two children` | 319 s | 005, needs-human | HUMAN | check-job PASS |
| 5b | `/story approve 005...` | 26 s | 005 ready by human; 006, 007 spawned | n/a | OK, launch block printed |
| 5c | two parallel `/story children 005...` sessions (second started 20 s later) | 460 s and 487 s | 006 and 007, both needs-human, r2 | HUMAN | No double claim; each session took one child; epic ended needs-human (0 ready, 2 needs-human). check-job PASS on all three. |
| 6 | `check-job --manifest --compare` | | | | `OK manifest unchanged (7 files)`. `git -C team status --short` empty. `doctor` OK. |

Reviewer findings worth noting: round 1 came back CHANGES from all four lenses on most jobs, and the single revision closed most of them. Typical catches: the stub controllers throw `not implemented`, no datasource exists, 404 body shape unspecified, recipient-vs-sender visibility, audit event fields and no PII in logs, fail-closed when the caller id is missing. The tech reviewer's "PASS" notes show it re-checked the code (stubs, `createdAt` typed `date` vs string, dependencies in package.json).

## additionalDirectories: answer

**Yes, subagents could read the dummy team repo.** From the session transcripts: the writer (`story-writer`) and the reviewers each issued `Read`/`Glob`/`Grep` calls on absolute paths under `/Users/ant/Documents/ai/story-factory-smoke-team` (openapi.json, both controllers, both models, docs/README.md, package.json) with no permission errors. `story.json` cites real sources (`openapi.json:3,4,6,8`, `transfer.controller.ts`, `transfer.model.ts`, `account.model.ts`), and `checks.md` reported `OK accounts-api:...` for every source and `OK GET /transfers/{id}` for the API operation. This held even in the first run, where Claude printed `Ignoring 3 permissions.allow entries from .claude/settings.json: this workspace has not been trusted`; so `settings.local.json` `additionalDirectories` applied to subagents. Caveat: this was one dummy repo on one machine; the work laptop's trust state and repo locations may differ.

## Bugs

1. **High: headless run stalls silently when the workspace is untrusted.** Claude ignores `.claude/settings.json` allow rules until the trust dialog is accepted, so `sf.py verdict` needed approval; the run ended after 153 s with exit 0, `is_error: false`, job stuck at stage `review`. Exact text: `Ignoring 3 permissions.allow entries from .claude/settings.json: this workspace has not been trusted.` Fix: `doctor` should warn when `~/.claude.json` has no `hasTrustDialogAccepted` for the repo path; TESTING.md should say to open `claude` once in the clone and accept trust.
2. **Medium: orchestrator issues compound shell commands that the allow rules do not cover.** Denied examples: `J=factory/jobs/002... && mkdir -p ... && python3 scripts/jira_stub.py ... > file`, `for k in ...; do ...; done`, `python3 ... ; echo "exit=$?"`, and `sed -n '/^## For the human/,/^## /p' <abs path>/decision.md` (seen in every run). In interactive use these become prompts. Fix: SKILL.md rule "one `sf.py` call per Bash call, no variables, loops or `sed`", plus an `sf.py human ID` subcommand that prints the `## For the human` section.
3. **Medium: stale claim blocks resume after a crash.** `/story resume` returned `BUSY 001-... Anthonys-MacBook-Pro.local:84779 ...` for a dead pid, and the session could not check liveness (`ps` denied). Fix: `claim` should treat a claim from the same host whose pid no longer exists as free.
4. **Medium (owner decision): 0 of 7 jobs reached READY.** Every job escalated, because the writer sets pii/auth/payments/regulatory flags on any bank transfer story and "open questions / product assumption" also gate. The READY path and `sf.py gate` OK branch were therefore not exercised end to end here. Suggested: owner to decide whether `product-decision`, assumptions and persistent ac CHANGES should force HUMAN, and test a plainly non-sensitive story (for example a docs or logging-format change).
5. **Low: Skill tool call to `pull-jira-ticket-stub` returned only `Execute skill: pull-jira-ticket-stub`**, no ticket; the orchestrator ran `python3 scripts/jira_stub.py KEY` itself. Works, but the real `pull-jira-ticket` may behave differently; verify on the laptop. Suggested: SKILL.md fallback sentence.
6. **Low: `escalate` on a blocked writer leaves `gate_reasons` and `flags` empty** (job 002, stage needs-human). Fix: have `escalate` append a reason such as `writer-blocked`.
7. **Low: `reviewer-invest` twice (jobs 004, 007) returned its review as a message without writing `review-invest.md`.** The skill's one retry handled it. Fix idea: stress "write the file, then reply with one line" in the agent prompt.
8. **Info: the writer cannot be resumed from a new session** (resume after a restart spawned a fresh writer from files); acceptable, but note the revision may differ in style.
9. **Info:** `duration_ms` in the JSON output reflects only the final turn (71 s for a 232 s run); use wall time.

## Rendered story excerpt (job 001, `story.md`)

> # Customer can view the status of a transfer they sent, by transfer id
>
> **As a** retail banking customer who has sent a transfer, **I want** to look up one of my transfers and see whether it is pending, completed or failed, **so that** I know whether the money has left my account yet and do not need to contact the bank to find out.
>
> **AC1 - Sender sees a pending transfer**
> - **Given** the transfer store holds transfer `tr-1001` with `fromAccountId` `acc-2001`, `toAccountId` `acc-2002`, `amount` 150.00, `status` `PENDING` ..., and account `acc-2001` has `ownerId` `cust-301`
> - **When** a request authenticated as customer `cust-301` calls `GET /transfers/tr-1001`
> - **Then** the response status is 200 and the body is exactly `{"id": "tr-1001", ...  "status": "PENDING", ...}`, with no other properties
>
> **AC5 - Another customer's transfer looks the same as a missing one** ... 404 with a body byte-identical to the AC4 body.

Quality: ACs are concrete (named ids, exact status codes and bodies), testable, grounded in the contract (`GET /transfers/{id}`, `TransferController.findById`, the stub controllers, `Account.ownerId`) and add the security cases a bank needs (recipient 404, fail-closed on missing caller, audit with no PII). 9 ACs is large for one story; the INVEST reviewer accepted it. Open questions were left as questions, not invented answers.

## Recommendations before the work laptop

1. Open `claude` in the factory clone once and accept the trust dialog; run `doctor`.
2. Pre-approve or allow the real `pull-jira-ticket` skill's tools, and confirm a bare `/pull-jira-ticket KEY` returns the ticket, then confirm the orchestrator gets the text via the Skill tool.
3. Use the new `check-job --manifest` before and `--compare` after.
4. Expect NEEDS-HUMAN on nearly everything in a bank domain; decide bug 4 first, or the owner will review every story.
5. Expect 3 to 8 minutes per story (about $1.5 to $3 each, with Opus writer) and about 8 minutes for a two-child epic run in parallel.
6. If a headless or interactive run stops at `review`, use `sf.py claim ID --force` then `/story resume ID`.

## Fixes (same day)

Each fix is a separate commit on main with a unit test and a decision record. Retests used the smoke clone pulled to the fixes (`/Users/ant/Documents/ai/story-factory-smoke`) and the same dummy team repo; the manifest stayed unchanged and `check-job` passed.

| Bug | Fix commit | Retest |
|---|---|---|
| 1 stalls when untrusted | `7dfbf1b` doctor warns (0050); `509f1a2` `sf.py settings` writes the allow rules and `Skill(<jira.skill>)` into `settings.local.json`, which Claude honours even when untrusted (0055) | Job 011, plain `/story` with no `--allowedTools`, folder still untrusted: ran to the approver in 290 s, no stall, no permission denials. |
| 2 compound commands | `e43aced` SKILL.md rule of one plain command per Bash call; new `sf.py human ID` (0053) | Jobs 008 to 011: no denials; the orchestrator used `sf.py human`. |
| 3 stale claim | `59f3be0` `claim` takes over a claim whose same-host pid is dead, under a directory flock (0051) | Unit tests (dead pid taken over; live, custom and other-host holders stay BUSY). Not re-run end to end. |
| 5 Jira Skill call errors | `509f1a2` (0055). Root cause: the `Skill` call needed a permission rule that the ignored shared settings did not provide, and the orchestrator then escalated. | Jobs 010 and 011 pulled the stub ticket through the Skill tool. Note: before the fix, strict ERROR handling made refine and bug runs escalate at intake (jobs 008, 009). |
| 6 empty gate_reasons on escalate | `8c3b8a7` `escalate` records `escalated: <why>` (0052) | Job 008 showed `gate_reasons: ["escalated: Jira pull failed ..."]`. |
| 7 invest review not saved | `175793e` reviewers told to Write, never reply with the review (0054) | Not reproducible on demand; no recurrence in jobs 010 and 011 (one run each). |

Left unfixed:

- **Bug 4 (0 of 7 jobs READY):** needs an owner decision on what should force NEEDS-HUMAN. Not touched. The READY path is still untested end to end.
- **Bug 8 (writer not resumable across sessions) and bug 9 (`duration_ms`):** Claude Code behaviour, nothing to fix here.
- `doctor` still warns about trust after fix 1; that is intentional (0050), and the run above shows the factory works without it.

## Testbed

The dummy team repo is versioned as `testbed/team-repo/` (plain files). `python3 scripts/sf.py testbed PATH` recreates it as a standalone git repo and prints the config snippet (decision 0056, section "Testbed" in `docs/TESTING.md`). The original instance stays at `/Users/ant/Documents/ai/story-factory-smoke-team`; the smoke clone stays at `/Users/ant/Documents/ai/story-factory-smoke`.
