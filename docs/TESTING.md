# Manual test plan (work laptop)

Run this on the work laptop with real Jira and real team repos. Nothing here writes to Jira or to a team repo. Do not paste ticket content into this file, a commit or a chat outside the approved tools.

## 1. Setup

1. Clone the factory somewhere that is not inside a team repo: `git clone git@github.com:AnthonyFlowers/story-factory.git` (or the HTTPS URL). Then `cd story-factory`.
   - Expect: a clean `git status`.
2. `python3 --version`.
   - Expect: 3.9 or newer.
3. `cp factory.config.example.json factory.config.json` and edit it (the file is gitignored):
   - `repos`: one entry per team repo, with an absolute `path`, a `name`, `openapi` (paths relative to the repo; use JSON files, YAML contracts are SKIPPED by the checks), `docs` and `notes`.
   - `team_docs`: the shared handbook or standards folders, absolute paths.
   - `deny_read`: absolute paths of repos the factory must not read.
   - `jira.skill`: `pull-jira-ticket`. `jira.project_key`: your project key.
4. `python3 scripts/sf.py settings`, then `python3 scripts/sf.py doctor`.
   - Expect: `settings` writes `.claude/settings.local.json` (read access to every repo and team-docs path, edit deny rules on them, and allow rules for `sf.py`, the Jira stub and the configured Jira skill). `doctor` prints `OK`. A `WARN: Claude Code has not trusted ...` line means the allow rules in `.claude/settings.json` are ignored: run `claude` once in the factory folder and accept the trust dialog, or headless runs stall at the first `sf.py` call.
5. `git config core.hooksPath scripts/hooks`.
6. `python3 -m unittest discover -s tests`.
   - Expect: all tests pass.
7. `python3 scripts/sf.py check-job --manifest`.
   - Expect: `manifest written: N files`. It hashes every file under every repo and team-docs path (skipping `.git` and `node_modules`) into `factory/jobs/.manifest.json`. Do this before every test session.

## 2. Wiring the real pull-jira-ticket

1. Make the skill available to Claude Code as a user-level skill, for example `~/.claude/skills/pull-jira-ticket/`. Never copy it into the factory repo. `pull-jira-ticket-stub` (in `.claude/skills/`) is for the unit tests only.
2. Start `claude` in the factory repo and run `/pull-jira-ticket <a real key>`.
   - Expect: the ticket comes back. Factory JSON, raw Jira REST JSON (`{"key":..., "fields":{...}}`) and markdown are all accepted. A failure must start with `ERROR:`.
3. If the skill asks for approval prompts, approve them, or add an allow rule for the skill's tools to `.claude/settings.local.json` (gitignored). `sf.py settings` already allows `Skill(<jira.skill>)`; add any further rules after running it, because `settings` rewrites that file.
   - Expect: later `/story` runs pull tickets without stopping.

## 3. Test 1: a first single story

1. In Claude Code, run `/story <a small real idea>`.
   - Expect, in order: a job folder `factory/jobs/NNN-slug/` is created and claimed; the Jira pull loop runs (only if the idea names keys); the writer drafts `story.json`; four reviewers run in parallel into `round-1/`; at most one revision (`round-2/`); the approver writes `decision.md`; `sf.py gate --apply` sets `ready` or `needs-human`.
2. Look at the job folder.
   - Expect: `job.json`, `brief.md`, `story.json`, `story.md`, `decision.md`, `round-N/{story.json,checks.md,review-invest.md,review-ac.md,review-tech.md,review-security.md}`.
3. `python3 scripts/sf.py list`.
   - Expect: one row with the final stage.
4. Open the dashboard (section 7).
   - Expect: the job sits in a terminal column.
5. Paste `story.md` into a scratch Jira issue (a test project, not a real one). Record whether headings, bold and lists converted.
   - Expect: unknown. This is unverified.
6. `python3 scripts/sf.py check-job <id>`.
   - Expect: `OK` lines and `RESULT: PASS`. Any `FAIL <check>: <detail>` line names the broken invariant.

## 4. Test 2: refine an existing ticket

1. `/story refine <KEY>` for a real ticket of moderate size.
   - Expect: `context/jira/` holds the ticket plus its parent and linked tickets (up to 1 hop and 8 tickets). `job.json` has `jira_key` set. `story.md` has a "Changes from the original ticket" section.
2. `python3 scripts/sf.py check-job <id>`.
   - Expect: `RESULT: PASS`.

## 5. Test 3: an epic with parallel children

1. `/story epic <KEY or idea>`.
   - Expect: the breakdown is written and reviewed like a story. When it is ready (or after `/story approve <id>`), the session creates the child jobs, prints a launch block listing each child, and stops.
2. Open 2 or 3 more Claude Code sessions in the factory repo. In each run `/story children <epic-id>`. Watch the dashboard.
   - Expect: no two sessions take the same child. Each session claims one child at a time until none are left.
3. Wait for all children to finish, then in any session run `python3 scripts/sf.py epic-status <epic-id>`.
   - Expect: one line per child, then `ALL-DONE ready=N needs-human=M`. The last session to finish sets the epic stage (`epic-status --apply`).
4. Recovery: if a session died and left a child claimed, run `python3 scripts/sf.py claim <child-id> --force`, then `/story resume <child-id>`.
5. `python3 scripts/sf.py check-job <epic-id>`, then `check-job <child-id>` for each child.
   - Expect: `RESULT: PASS` for each. While children are still running, use `check-job <epic-id> --allow-running`.

## 6. Test 4: escalation

1. `/story <an idea that touches PII, authentication or payments>`.
   - Expect: stage `needs-human`. `decision.md` ends with `## For the human` and numbered, specific questions. `sf.py job <id>` shows `gate_reasons` such as `flag:pii`.
2. Answer by either `/story approve <id>` or `/story rework <id> "<note>"`.
   - Expect for approve: stage `ready`, `approved_by` `human`. Expect for rework: `rework-1.md`, a new round folder, and a fresh decision.
3. `python3 scripts/sf.py check-job <id>`.
   - Expect: `RESULT: PASS`.

## 7. Dashboard

1. `python3 scripts/sf.py dashboard`, then open http://127.0.0.1:8765/dashboard.html.
   - Expect: jobs appear in columns and update every 2 seconds.
2. `lsof -nP -iTCP:8765 -sTCP:LISTEN`.
   - Expect: `127.0.0.1:8765` only.
3. Browser dev tools, network tab, reload the page.
   - Expect: requests to localhost only.
4. Click the Copy button on a ready job.
   - Expect: the story text is on the clipboard.

## 8. Copilot lite

1. In VS Code, open the factory folder, switch Copilot Chat to agent mode and run `/story-lite <a small idea>`.
   - Expect: the same job folder layout as Claude, with `"harness": "copilot-lite"` in `job.json`.
2. Record:
   - whether the prompt's `tools` list (`read`, `search`, `edit`, `execute`) was accepted;
   - whether `${input:args:...}` behaved (asked for the idea when none was typed);
   - whether the `pull-jira-ticket` skill is visible to Copilot (VS Code reads `~/.claude/skills`);
   - which model answered.
3. If the skill is not visible, the prompt stops and prints what to do: run your Jira skill, save its output as `context/jira/<KEY>.json` (or `.md`) in the job folder, then `/story-lite resume <id>`.
   - Expect: after the manual drop, the run continues and `check-job <id>` says `RESULT: PASS`.

## 9. After testing

1. `python3 scripts/sf.py check-job --manifest --compare`.
   - Expect: `OK manifest unchanged (N files)`. Any `CHANGED`, `ADDED` or `REMOVED` line is a bug: stop and report it.
2. `git status --porcelain`.
   - Expect: no job files and no `factory.config.json`. Never commit anything from `factory/jobs`.
3. `python3 scripts/sf.py doctor`.
   - Expect: `OK`.
4. Record results in the list at the end of this file or in your own notes. Record stage, rounds, flags, pass or fail and anything odd. Never record real ticket content.

## Known unverified points

- Whether Jira converts pasted `story.md` (headings, bold, lists).
- Copilot: whether the `tools` names in `story-lite.prompt.md` are valid, and whether `${input:...}` works.
- Whether subagents can read `permissions.additionalDirectories` (the writer and reviewers must see the team repos; if they report missing sources, this is the cause).
- Whether `chat.useAgentsMdFile` is on by default (the lite prompt reads `AGENTS.md` explicitly anyway).

## Test results

- (date, test, stage, rounds, flags, pass or fail, notes)

## Testbed

`testbed/team-repo/` holds a tiny dummy LoopBack-style API (`accounts-api`: accounts and transfers, `openapi.json` with `GET /accounts/{id}`, `POST /transfers`, `GET /transfers/{id}`, no work data). It is plain files with no `.git`, and no config points at it by default, so the checks never treat it as a team repo. To use it:

```bash
python3 scripts/sf.py testbed /absolute/path/to/team-repo-copy   # copies it, git init, one commit, prints the config snippet
```

Put the printed `repos` and `jira` entries into `factory.config.json`, then run `sf.py settings`, `sf.py doctor` and `sf.py check-job --manifest` as in section 1. Run it against a throwaway clone of the factory. Findings from the first run are in `docs/test-reports/2026-10-13-claude-smoke.md`.
