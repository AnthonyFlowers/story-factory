---
tags: [project, story-factory, design, claude-code, copilot, jira]
created: 2026-10-13
---

# story-factory: design

Part of [story-factory](../README.md). This note is the architecture. Steps [01](steps/01-scaffold-schema-renderer.md) to [08](steps/08-e2e-dry-run.md) build it, and each step stands alone. The owner decisions on the hub are binding. Where this note seems to disagree with them, the hub wins and this note is wrong.

## 1. What it is

story-factory is a Claude Code repo that turns an idea or a Jira key into a reviewed story. The story is stored as `story.json` and rendered to markdown. It is modelled on zazencodes' software-factory-claude-code: one orchestrator skill, subagents that each write one file, parallel reviewers, an approver, job folders, a backlog, and a polling HTML dashboard.

The factory has no code, build, merge or Jira write. A story ends READY, meaning the final story is in the job folder and the owner pastes it into Jira by hand. Otherwise it ends NEEDS-HUMAN, with the exact questions for the owner.

- Repo: a private repo `AnthonyFlowers/story-factory` on the owner's personal GitHub, at `~/Documents/ai/story-factory` on the Mac.
  - The owner creates the remote and pushes. The steps only `git init`.
  - It is cloned onto the work laptop (M1 Pro 32 GB, bank).
  - It points at team repos by absolute path in a gitignored config.
- Work data never enters git. These paths are all gitignored:
  - `factory/jobs/`
  - `factory/backlog.md`
  - `factory.config.json`
  - `templates/local/`
  - `.claude/settings.local.json`
- A pre-commit hook and `sf.py doctor` check this.

## 2. The loop

```
 /story <idea> | bug <text> | spike <q> | refine <KEY> | epic <idea|KEY> | next
                │
                ▼
      ┌────────────────────┐  sf.py new-job → job.json + brief.md
      │ intake (orchestr.) │  pull-jira-ticket (READ ONLY) → context/jira/<KEY>.json|.md
      └─────────┬──────────┘  (keys from the idea + links/parent, 1 hop, max 8)
                ▼
      ┌────────────────────┐
      │    story-writer    │◄───────────────────────────────┐
      │        opus        │  writes story.json             │
      └─────────┬──────────┘                                │
                ▼ sf.py validate → render (story.md) → checks (round-N/checks.md + snapshot)
   ┌────────────┬──────────┴─┬──────────────┐               │
   ▼            ▼            ▼              ▼               │
┌────────┐ ┌────────┐ ┌────────────┐ ┌────────────┐         │
│ invest │ │   ac   │ │    tech    │ │  security  │         │
│ sonnet │ │ sonnet │ │   sonnet   │ │    opus    │         │
└───┬────┘ └───┬────┘ └─────┬──────┘ └─────┬──────┘         │
    └──────────┴─────┬──────┴──────────────┘                │
                     ▼                                      │
           ┌──────────────────┐  any CHANGES and the        │
           │   WAIT FOR ALL   ├─ writer has not revised ────┘  resume writer (once)
           └────────┬─────────┘
                    ▼ all PASS, or round 2 finished
           ┌──────────────────┐
           │  story-approver  │ opus → decision.md (READY | NEEDS-HUMAN + checklist)
           └────────┬─────────┘
                    ▼ sf.py gate --apply (deterministic floor: security reviewer's flags, CHANGES left, invalid reviews)
        READY ──────┴────── NEEDS-HUMAN ◄── /story approve <id>  (→ READY, approved_by human)
          │                      └───────── /story rework <id> <note> (→ writer, fresh revision)
          ▼
   story.md, ready to paste into Jira by hand
```

**Epic variant.**
1. The writer drafts `story.json` with `type: "epic"`, which holds the goal, success criteria and a list of children.
2. The same four reviewers check the breakdown: gaps, overlap, order, size and risk spread.
3. The approver rules on the breakdown.
4. On READY, or after `/story approve`, `sf.py spawn-children` creates one ordinary job per child with `parent` set. The epic's stage becomes `children`.
5. The orchestrator runs each child through the full loop above, one at a time.
6. When every child has finished, the epic becomes `ready` if all children are ready, otherwise `needs-human`.

## 3. Commands (final names)

| Command | What it does |
|---|---|
| `/story <idea>` | new single story |
| `/story bug <text>` | new bug |
| `/story spike <question>` | new spike |
| `/story epic <idea or KEY>` | epic breakdown, then every child through the loop |
| `/story refine <KEY>` | pull an existing ticket and rewrite it as a reviewed story; the type follows the ticket's issue type |
| `/story next` | run the first unchecked `factory/backlog.md` item. A line can start `bug:`, `spike:`, `epic:` or `refine:`; a bare line is a story |
| `/story approve <id>` | owner signs off a `needs-human` job: it becomes `ready` with `approved_by: human`. For an epic, it also starts the children |
| `/story rework <id> <note>` | send a `needs-human` or `ready` job back to the writer with the note; the job gets a fresh single revision |
| `/story resume <id>` | continue a job from its recorded stage, after a crash or to run an epic child |
| `/story render <id> [md]` | re-render `story.json`; `md` is the default and the only format in v1 |

Copilot lite uses the same subcommands through a single prompt, `/story-lite`.

## 4. Repo layout

```
story-factory/
  README.md                        what it is, setup on Mac and work laptop, commands
  AGENTS.md                        rules for any agent working ON this repo (tests, no work data)
  CLAUDE.md                        one line: @AGENTS.md
  .gitignore                       factory/jobs/ factory/backlog.md factory.config.json templates/local/ .claude/settings.local.json __pycache__/
  factory.config.example.json      committed example; real factory.config.json is gitignored
  .claude/
    settings.json                  deny WebFetch, WebSearch; allow Bash(python3 scripts/sf.py *)
    skills/story/SKILL.md          the orchestrator (/story)
    skills/pull-jira-ticket-stub/SKILL.md   test double for the owner's pull-jira-ticket
    agents/story-writer.md         opus    → story.json
    agents/reviewer-invest.md      sonnet  → round-N/review-invest.md
    agents/reviewer-ac.md          sonnet  → round-N/review-ac.md
    agents/reviewer-tech.md        sonnet  → round-N/review-tech.md
    agents/reviewer-security.md    opus    → round-N/review-security.md
    agents/story-approver.md       opus    → decision.md
  .github/prompts/story-lite.prompt.md     Copilot lite
  schemas/story.schema.json        the story contract (section 6)
  schemas/job.schema.json          job.json contract (section 7)
  schemas/jira-ticket.schema.json  preferred shape of a pulled ticket (section 11)
  templates/default.json           default team template + definition of ready (section 9)
  templates/local/                 gitignored team templates
  scripts/sf.py                    CLI: the orchestrator's deterministic tools
  scripts/sflib/                   config, jobs, schema (mini validator), checks, gate, verdicts, backlog, settings, server
  scripts/sflib/renderers/         markdown.py (+ future formats)
  scripts/jira_stub.py             stub backend for pull-jira-ticket-stub
  scripts/hooks/pre-commit         refuses commits of work-data paths
  factory/dashboard.html           local board
  factory/backlog.example.md
  factory/jobs/                    gitignored runtime state
  tests/                           unittest suites + fixtures (dummy data only)
```

### Job folder

```
factory/jobs/004-refine-demo-101/
  job.json                 orchestrator only (through sf.py)
  brief.md                 sf.py new-job/brief: idea verbatim, type, repo/OpenAPI/doc paths, template, rules
  context/jira/DEMO-101.json    orchestrator, from pull-jira-ticket (.md if the skill returned markdown)
  story.json               story-writer (the one artefact)
  story.md                 sf.py render (re-rendered after each writer pass)
  round-1/story.json       sf.py checks: snapshot of what was reviewed
  round-1/checks.md        sf.py checks: schema, DoR auto checks, source refs, API ops, flags
  round-1/review-{invest,ac,tech,security}.md
  round-2/...              only if the writer revised
  rework-1.md              orchestrator, from /story rework
  decision.md              story-approver (or sf.py escalate on a block or error)
```

## 5. Agents

All agents get their context from files, never from the conversation, and each writes exactly one file. None has Bash, WebFetch or WebSearch, so team repos are read with Read, Grep and Glob only. Every prompt starts:

`Job folder: <abs job dir>. Repo root: <abs factory root>.`

| Agent | Model | Reads | Writes | Role |
|---|---|---|---|---|
| `story-writer` | opus | `brief.md`, `context/jira/*`, the repos, OpenAPI files and team docs that `brief.md` lists, the template, and on revision `round-N/review-*.md` or `rework-k.md` | `story.json` | Drafts or revises the story. Cites every claim in `sources`, uses Given/When/Then ACs, gives no estimates, and sets `meta.blocked` when it cannot proceed. Resumed with SendMessage for its one revision. |
| `reviewer-invest` | sonnet | `round-N/story.json`, `checks.md`, `brief.md` | `round-N/review-invest.md` | Checks INVEST and the definition-of-ready items marked `review`. For an epic: whether the children are independent, small and well ordered, and whether they cover the goal. |
| `reviewer-ac` | sonnet | same | `round-N/review-ac.md` | Checks the ACs are testable, single-behaviour and Given/When/Then; that happy, error, edge and authz cases are covered; and that there are no vague words. For a bug: the fix plus a regression AC. For a spike: deliverable ACs. |
| `reviewer-tech` | sonnet | same + repos + OpenAPI | `round-N/review-tech.md` | Checks the source refs are real, every endpoint or field exists or is declared new in `api_impact`, and the story fits the repo's LoopBack patterns. Flags `breaking-contract`, `data-migration` and `third-party`. |
| `reviewer-security` | opus | same + repos + OpenAPI + team docs | `round-N/review-security.md` | Bank lens: OWASP API Top 10 (2023), PII minimisation and masking, authz ACs, audit events, logging, retention and regulatory hooks. Raises flags even on PASS. |
| `story-approver` | opus | everything in the job folder | `decision.md` | Makes the final call (READY or NEEDS-HUMAN) and writes the DoR checklist with evidence and the exact questions for the owner. |

## 6. `story.json` schema

JSON Schema 2020-12, restricted to a subset that the stdlib mini-validator in `scripts/sflib/schema.py` implements:
- `type` (string or array)
- `properties`, `required`, `additionalProperties: false`
- `enum`, `const`
- `items`, `minItems`
- `minLength`, `maxLength`, `pattern`, `minimum`
- local `$ref` to `#/$defs/*`
- `allOf` with `if` and `then`

`additionalProperties: false` everywhere is how "no estimates" is enforced: a `story_points` key fails validation.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "story-factory/story.schema.json",
  "title": "story-factory story",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "id", "type", "title", "acceptance_criteria", "out_of_scope", "dependencies", "sources", "meta"],
  "properties": {
    "schema_version": { "const": 1 },
    "id": { "type": "string", "pattern": "^[0-9]{3}-[a-z0-9-]+$" },
    "type": { "enum": ["story", "bug", "spike", "epic"] },
    "title": { "type": "string", "minLength": 5, "maxLength": 120 },
    "jira": { "$ref": "#/$defs/jira" },
    "refines": { "$ref": "#/$defs/refines" },
    "user_story": { "$ref": "#/$defs/user_story" },
    "context": { "type": "string", "minLength": 1 },
    "acceptance_criteria": { "type": "array", "items": { "$ref": "#/$defs/ac" } },
    "tech_notes": { "type": "array", "items": { "type": "string", "minLength": 1 } },
    "api_impact": { "type": "array", "items": { "$ref": "#/$defs/api_change" } },
    "out_of_scope": { "type": "array", "items": { "type": "string", "minLength": 1 } },
    "dependencies": { "type": "array", "items": { "$ref": "#/$defs/dependency" } },
    "assumptions": { "type": "array", "items": { "$ref": "#/$defs/assumption" } },
    "open_questions": { "type": "array", "items": { "type": "string", "minLength": 1 } },
    "risk_flags": { "type": "array", "items": { "$ref": "#/$defs/flag" } },
    "bug": { "$ref": "#/$defs/bug" },
    "spike": { "$ref": "#/$defs/spike" },
    "epic": { "$ref": "#/$defs/epic" },
    "sources": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/source" } },
    "extra": { "type": "object" },
    "meta": { "$ref": "#/$defs/meta" }
  },
  "allOf": [
    { "if": { "properties": { "type": { "const": "story" } } },
      "then": { "required": ["user_story", "context"], "properties": { "acceptance_criteria": { "minItems": 2 } } } },
    { "if": { "properties": { "type": { "const": "bug" } } },
      "then": { "required": ["bug", "context"], "properties": { "acceptance_criteria": { "minItems": 2 } } } },
    { "if": { "properties": { "type": { "const": "spike" } } },
      "then": { "required": ["spike", "context"], "properties": { "acceptance_criteria": { "minItems": 1 } } } },
    { "if": { "properties": { "type": { "const": "epic" } } },
      "then": { "required": ["epic", "context"] } }
  ],
  "$defs": {
    "jira_key": { "type": "string", "pattern": "^[A-Z][A-Z0-9_]+-[0-9]+$" },
    "flag": { "enum": ["pii", "auth", "payments", "audit", "regulatory", "data-migration", "breaking-contract", "third-party", "product-decision"] },
    "jira": {
      "type": "object", "additionalProperties": false, "required": ["issue_type"],
      "properties": {
        "key": { "type": ["string", "null"], "pattern": "^[A-Z][A-Z0-9_]+-[0-9]+$" },
        "issue_type": { "enum": ["Story", "Bug", "Spike", "Epic", "Task"] },
        "project_key": { "type": "string" },
        "parent_key": { "type": ["string", "null"] },
        "labels": { "type": "array", "items": { "type": "string" } },
        "components": { "type": "array", "items": { "type": "string" } },
        "links": { "type": "array", "items": {
          "type": "object", "additionalProperties": false, "required": ["relation", "key"],
          "properties": { "relation": { "type": "string" }, "key": { "$ref": "#/$defs/jira_key" } } } }
      }
    },
    "refines": {
      "type": "object", "additionalProperties": false, "required": ["key", "changes"],
      "properties": {
        "key": { "$ref": "#/$defs/jira_key" },
        "changes": { "type": "array", "minItems": 1, "items": {
          "type": "object", "additionalProperties": false, "required": ["field", "summary", "reason"],
          "properties": { "field": { "type": "string" }, "summary": { "type": "string" }, "reason": { "type": "string" } } } }
      }
    },
    "user_story": {
      "type": "object", "additionalProperties": false, "required": ["as_a", "i_want", "so_that"],
      "properties": {
        "as_a": { "type": "string", "minLength": 3 },
        "i_want": { "type": "string", "minLength": 3 },
        "so_that": { "type": "string", "minLength": 3 }
      }
    },
    "ac": {
      "type": "object", "additionalProperties": false, "required": ["id", "given", "when", "then"],
      "properties": {
        "id": { "type": "string", "pattern": "^AC[0-9]+$" },
        "title": { "type": "string" },
        "given": { "type": "string", "minLength": 3 },
        "when": { "type": "string", "minLength": 3 },
        "then": { "type": "string", "minLength": 3 },
        "and": { "type": "array", "items": { "type": "string", "minLength": 3 } },
        "kind": { "enum": ["happy", "edge", "error", "security", "regression", "deliverable"] }
      }
    },
    "api_change": {
      "type": "object", "additionalProperties": false, "required": ["contract", "operation", "change", "breaking"],
      "properties": {
        "contract": { "type": "string", "pattern": "^[a-z0-9-]+:.+$" },
        "operation": { "type": "string", "pattern": "^(GET|POST|PUT|PATCH|DELETE) /" },
        "change": { "enum": ["none", "add", "modify", "remove"] },
        "breaking": { "enum": ["yes", "no", "unknown"] },
        "detail": { "type": "string" }
      }
    },
    "dependency": {
      "type": "object", "additionalProperties": false, "required": ["ref", "kind", "reason"],
      "properties": {
        "ref": { "type": "string", "minLength": 1 },
        "kind": { "enum": ["blocked-by", "blocks", "relates", "external"] },
        "reason": { "type": "string", "minLength": 3 }
      }
    },
    "assumption": {
      "type": "object", "additionalProperties": false, "required": ["text", "kind"],
      "properties": { "text": { "type": "string", "minLength": 3 }, "kind": { "enum": ["product", "technical"] } }
    },
    "bug": {
      "type": "object", "additionalProperties": false, "required": ["observed", "expected", "steps"],
      "properties": {
        "observed": { "type": "string", "minLength": 3 },
        "expected": { "type": "string", "minLength": 3 },
        "steps": { "type": "array", "minItems": 1, "items": { "type": "string" } },
        "environment": { "type": "string" },
        "evidence": { "type": "array", "items": { "type": "string" } }
      }
    },
    "spike": {
      "type": "object", "additionalProperties": false, "required": ["question", "outputs"],
      "properties": {
        "question": { "type": "string", "minLength": 10 },
        "approach": { "type": "array", "items": { "type": "string" } },
        "outputs": { "type": "array", "minItems": 1, "items": { "type": "string" } }
      }
    },
    "epic": {
      "type": "object", "additionalProperties": false, "required": ["goal", "children"],
      "properties": {
        "goal": { "type": "string", "minLength": 10 },
        "success_criteria": { "type": "array", "items": { "type": "string" } },
        "children": { "type": "array", "minItems": 2, "items": {
          "type": "object", "additionalProperties": false, "required": ["ref", "type", "title", "summary", "order"],
          "properties": {
            "ref": { "type": "string", "pattern": "^C[0-9]+$" },
            "type": { "enum": ["story", "bug", "spike"] },
            "title": { "type": "string", "minLength": 5, "maxLength": 120 },
            "summary": { "type": "string", "minLength": 20 },
            "depends_on": { "type": "array", "items": { "type": "string", "pattern": "^C[0-9]+$" } },
            "order": { "type": "integer", "minimum": 1 }
          } } }
      }
    },
    "source": {
      "type": "object", "additionalProperties": false, "required": ["kind", "ref"],
      "properties": {
        "kind": { "enum": ["code", "openapi", "jira", "doc", "idea", "rework"] },
        "ref": { "type": "string", "minLength": 1 },
        "note": { "type": "string" }
      }
    },
    "meta": {
      "type": "object", "additionalProperties": false, "required": ["round"],
      "properties": {
        "round": { "type": "integer", "minimum": 1 },
        "blocked": { "type": ["string", "null"] },
        "revision_log": { "type": "array", "items": {
          "type": "object", "additionalProperties": false, "required": ["round", "finding", "action"],
          "properties": { "round": { "type": "integer" }, "finding": { "type": "string" }, "action": { "type": "string" } } } }
      }
    }
  }
}
```

**Ref conventions.**
- `code`, `openapi` and `doc` sources, and `api_impact.contract`, use `<name>:<relative path>[:<line>]`, where `<name>` is a `repos[].name` or `team_docs[].name` from the config.
- `jira` sources use the key.
- `idea` and `rework` sources use `brief` and `rework-<k>.md`.

`sf.py checks` verifies that every path exists and that every `modify`, `remove` or `none` operation exists in a JSON OpenAPI file. A YAML contract is reported as `SKIPPED (yaml)`, because the stdlib has no YAML parser. LoopBack's `npm run openapi-spec` emits JSON.

### Example: story (a refine)

```json
{
  "schema_version": 1,
  "id": "004-refine-demo-101",
  "type": "story",
  "title": "Filter account statements by date range",
  "jira": { "key": "DEMO-101", "issue_type": "Story", "project_key": "DEMO", "parent_key": "DEMO-100",
            "labels": ["statements"], "components": ["accounts-api"],
            "links": [{ "relation": "relates to", "key": "DEMO-102" }] },
  "refines": { "key": "DEMO-101", "changes": [
    { "field": "acceptance_criteria", "summary": "Replaced 'works for any dates' with three Given/When/Then criteria", "reason": "The original criterion was not testable" } ] },
  "user_story": { "as_a": "retail banking customer", "i_want": "to list my statements for a date range",
                  "so_that": "I can find last quarter's statements without paging through all of them" },
  "context": "Statements are served by `StatementController.find` at `GET /accounts/{accountId}/statements`, which returns every statement for the account, newest first.",
  "acceptance_criteria": [
    { "id": "AC1", "kind": "happy", "given": "account A has statements dated 2026-01-31, 2026-02-28 and 2026-03-31",
      "when": "its owner calls GET /accounts/A/statements?from=2026-02-01&to=2026-03-31",
      "then": "the response is 200 with exactly the 2026-02-28 and 2026-03-31 statements, newest first" },
    { "id": "AC2", "kind": "error", "given": "any account owned by the caller",
      "when": "the caller sends a from date later than the to date",
      "then": "the response is 400 with error code INVALID_DATE_RANGE" },
    { "id": "AC3", "kind": "security", "given": "account B belongs to another customer",
      "when": "the caller requests GET /accounts/B/statements?from=2026-01-01&to=2026-03-31",
      "then": "the response is 404, the same as without the filter" }
  ],
  "tech_notes": ["Filter in the repository query, not in memory.", "Dates are inclusive calendar dates."],
  "api_impact": [ { "contract": "accounts-api:openapi.json", "operation": "GET /accounts/{accountId}/statements",
                    "change": "modify", "breaking": "no", "detail": "Add optional query parameters from and to (format: date)." } ],
  "out_of_scope": ["Filtering by amount or statement type", "Mobile app UI"],
  "dependencies": [],
  "assumptions": [ { "text": "Either parameter may be sent alone", "kind": "technical" } ],
  "open_questions": [],
  "risk_flags": [],
  "sources": [
    { "kind": "jira", "ref": "DEMO-101", "note": "original ticket" },
    { "kind": "code", "ref": "accounts-api:src/controllers/statement.controller.ts", "note": "find()" },
    { "kind": "openapi", "ref": "accounts-api:openapi.json", "note": "GET /accounts/{accountId}/statements" }
  ],
  "extra": {},
  "meta": { "round": 1, "blocked": null, "revision_log": [] }
}
```

### Example: bug

```json
{
  "schema_version": 1, "id": "005-statements-500-empty", "type": "bug",
  "title": "Statements list returns 500 for an account with no statements",
  "jira": { "key": "DEMO-102", "issue_type": "Bug", "project_key": "DEMO", "labels": [], "components": ["accounts-api"], "links": [] },
  "context": "`StatementController.find` reads `statements[0].currency` to build the response envelope.",
  "bug": { "observed": "GET /accounts/{accountId}/statements returns 500: TypeError reading 'currency' of undefined",
           "expected": "200 with an empty items array",
           "steps": ["Create an account with no statements", "Call GET /accounts/{accountId}/statements as its owner"],
           "environment": "accounts-api main, local", "evidence": ["Stack trace in DEMO-102"] },
  "acceptance_criteria": [
    { "id": "AC1", "kind": "happy", "given": "account A has no statements", "when": "its owner calls GET /accounts/A/statements",
      "then": "the response is 200 with body {\"items\": []}" },
    { "id": "AC2", "kind": "regression", "given": "account A has one statement", "when": "its owner calls GET /accounts/A/statements",
      "then": "the response is the same as before the fix" }
  ],
  "tech_notes": ["Add a regression test beside the existing controller acceptance tests."],
  "api_impact": [ { "contract": "accounts-api:openapi.json", "operation": "GET /accounts/{accountId}/statements",
                    "change": "none", "breaking": "no", "detail": "Contract already allows an empty items array." } ],
  "out_of_scope": ["Changing the envelope shape"], "dependencies": [], "open_questions": [], "risk_flags": [],
  "sources": [ { "kind": "jira", "ref": "DEMO-102" }, { "kind": "code", "ref": "accounts-api:src/controllers/statement.controller.ts" } ],
  "meta": { "round": 1, "blocked": null, "revision_log": [] }
}
```

### Example: spike (no timebox, because estimates are excluded)

```json
{
  "schema_version": 1, "id": "006-spike-statement-pdf", "type": "spike",
  "title": "Spike: render statement PDFs inside accounts-api",
  "context": "Customers ask support for PDF statements. accounts-api has no document generation today.",
  "spike": { "question": "Can accounts-api render a statement PDF with a library on the team's approved list, without a new service?",
             "approach": ["Check team-docs:approved-dependencies.md", "Prototype one statement on a throwaway branch"],
             "outputs": ["A one-page decision note with one recommendation", "A sample PDF made from fixture data"] },
  "acceptance_criteria": [
    { "id": "AC1", "kind": "deliverable", "given": "the spike is finished", "when": "the team reads the decision note",
      "then": "it names one option, its licence, and whether a new service is needed" } ],
  "out_of_scope": ["Production code", "Storage of generated PDFs"], "dependencies": [], "open_questions": [], "risk_flags": [],
  "sources": [ { "kind": "idea", "ref": "brief" }, { "kind": "doc", "ref": "team-docs:approved-dependencies.md" } ],
  "meta": { "round": 1, "blocked": null, "revision_log": [] }
}
```

### Example: epic

```json
{
  "schema_version": 1, "id": "007-statement-self-service", "type": "epic",
  "title": "Statement self-service",
  "jira": { "key": "DEMO-100", "issue_type": "Epic", "project_key": "DEMO", "labels": [], "components": [], "links": [] },
  "context": "Support handles about a third of statement requests by hand (DEMO-100).",
  "epic": { "goal": "Customers find and download their own statements without calling support.",
            "success_criteria": ["Every statement from the last 24 months can be listed by date range and downloaded"],
            "children": [
              { "ref": "C1", "type": "story", "title": "Filter statements by date range", "summary": "Add optional from/to query parameters to GET /accounts/{accountId}/statements.", "depends_on": [], "order": 1 },
              { "ref": "C2", "type": "spike", "title": "Server-side statement PDFs", "summary": "Decide whether accounts-api can render PDFs with an approved library.", "depends_on": [], "order": 2 },
              { "ref": "C3", "type": "story", "title": "Download a statement as PDF", "summary": "Add GET /accounts/{accountId}/statements/{statementId}/pdf using the spike's choice.", "depends_on": ["C2"], "order": 3 } ] },
  "acceptance_criteria": [], "out_of_scope": ["Paper statement opt-out"], "dependencies": [], "open_questions": [],
  "risk_flags": ["pii"],
  "sources": [ { "kind": "jira", "ref": "DEMO-100" }, { "kind": "openapi", "ref": "accounts-api:openapi.json" } ],
  "meta": { "round": 1, "blocked": null, "revision_log": [] }
}
```

## 7. `job.json` and its state machine

The orchestrator is the only writer of `job.json`, and it always writes through `python3 scripts/sf.py job ...`, which rewrites the whole file atomically. The dashboard reads it.

```json
{ "id": "004-refine-demo-101", "type": "story", "mode": "refine", "harness": "claude",
  "idea": "refine DEMO-101", "jira_key": "DEMO-101", "parent": null, "children": {},
  "title": "Filter account statements by date range",
  "stage": "review", "round": 2, "revisions_used": 1,
  "reviews": { "invest": "PASS", "ac": "PASS", "tech": "pending", "security": "CHANGES" },
  "flags": ["pii"], "decision": null, "approved_by": null, "gate_reasons": [],
  "writer_agent": "a1b2c3", "created": "2026-10-13T09:00:00Z", "updated": "2026-10-13T09:12:41Z" }
```

| Stage | Entered when | Leaves to |
|---|---|---|
| `intake` | `sf.py new-job` | `draft` once the Jira pulls are done. A failed pull goes to `needs-human` through `sf.py escalate` |
| `draft` | writer spawned or resumed | `review` when `story.json` validates (one validation-fix resume is allowed, and it does not count as a revision); `needs-human` if `meta.blocked` is set or it is still invalid |
| `review` | `sf.py checks --round N`; `reviews` reset to `pending` | `approve` if all PASS or `revisions_used == 1`; `draft` if any CHANGES and `revisions_used == 0` |
| `approve` | approver spawned | `ready` or `needs-human`, decided by `sf.py gate --apply` |
| `children` | an epic's breakdown is READY or approved; `sf.py spawn-children` | `ready` if every child is ready, otherwise `needs-human` (`sf.py epic-status --apply`) |
| `ready` | terminal; `approved_by` is `agent` or `human` | `draft` on `/story rework` |
| `needs-human` | terminal until the owner acts | `ready` on `/story approve`; `draft` on `/story rework`, which resets `revisions_used` to 0 |

- `type` is one of `story`, `bug`, `spike` or `epic`.
- `mode` is `new` or `refine`.
- `harness` is `claude` or `copilot-lite`.
- `reviews` holds the current round only; earlier rounds live in their `round-N/` folders.
- `flags` is the union of `story.risk_flags`, the final round's review `FLAGS` lines and the decision's `FLAGS` line. It is a record; only the security review's `FLAGS` line blocks (section 9).

## 8. Verdict formats

`round-N/review-<lens>.md`:

```markdown
VERDICT: PASS | CHANGES
FLAGS: none | pii, auth

## Findings
1. [/acceptance_criteria/2/then] <problem, why it matters, the change wanted>

## Notes
Non-blocking observations. Optional.
```

- Line 1 is exactly `VERDICT: PASS` or `VERDICT: CHANGES`.
- Line 2 is exactly `FLAGS: none` or a comma-separated list from the flag vocabulary.
- Findings cite a JSON Pointer into `story.json`, or `[general]`. Write "None." when there are none.

`decision.md`:

```markdown
READY | NEEDS-HUMAN
FLAGS: none | pii

## Why
Two or three sentences.

## Definition of ready
- DOR1 met: <evidence>
- DOR5 not met: <evidence>

## Acceptance criteria
- AC1: testable / not, and why

## For the human
Only for NEEDS-HUMAN: numbered questions, each answerable in one line, naming the story.json field it changes.
```

`sf.py verdict <file>` parses either format. It prints `PASS flags=none`, `CHANGES flags=pii,auth`, `READY flags=none` or `NEEDS-HUMAN flags=pii` and exits 0, or prints `INVALID <reason>` and exits 1.

## 9. Escalation rules for a bank

There are two layers.

**1. The approver (judgment) marks NEEDS-HUMAN when the story:**
- **pii**: adds, exposes, exports, logs or retains customer personal data. This includes names, account or card numbers, tax IDs, addresses, date of birth and contact details, and any masking change.
- **auth**: touches authentication, authorisation, roles, entitlements, sessions or tokens, MFA or service credentials, or adds an endpoint whose object-level access rule is not stated in an AC.
- **payments**: moves money or changes balances, fees, interest, limits, ledger postings, currency or rounding.
- **audit**: creates or changes an audit trail, or changes who-did-what logging.
- **regulatory**: involves disclosures, consumer-protection rules, KYC/AML or sanctions, card data (PCI DSS), privacy notices, or record retention, for example under GLBA, Reg E or BSA. These are examples; the reviewer names the concern, not a legal conclusion.
- **data-migration**: changes a schema, backfills, deletes, archives or bulk-updates data, or changes retention.
- **breaking-contract**: has any `api_impact` with `breaking: yes` or `unknown`.
- **third-party**: adds a vendor, an outbound call or new data sharing.
- **product-decision**: carries a product-kind assumption, or covers pricing, eligibility, or customer-facing legal or marketing copy.

Since decision 0057 the list above is what the security reviewer judges; the approver marks NEEDS-HUMAN when the security review raises a blocking flag, when CHANGES remain after round 2, or when reviewers disagree. Open questions and assumptions do not block.

**2. `sf.py gate --apply` (deterministic floor)** forces `needs-human` and records `gate_reasons`, even when `decision.md` says READY, if any of these hold:
- the final-round `review-security.md` `FLAGS:` line meets `config.escalation.always_human` (default `pii`, `auth`, `payments`, `regulatory`). This is the only flag source that blocks. The writer's `risk_flags`, other reviewers' flags and the decision's flags are recorded in `job.json` `flags` but never block.
- any final-round review is missing or invalid, which includes a missing `FLAGS:` line (the safe default is a human).
- any final-round review says CHANGES.
- `decision.md` is missing or invalid, or says NEEDS-HUMAN (the approver's own escalation).
- `checks.md` reports a schema error or a MISSING source.
- a `config.escalation.extra_terms` word appears anywhere in `story.json`. This matching is case-insensitive.

## 10. Template plug-in format

The config key `"template": "<name>"` loads `templates/<name>.json`, or `templates/local/<name>.json`, which is gitignored for team templates. The template controls section order, headings, required sections per type, the definition of ready, and custom sections stored in `story.extra.<id>`.

```json
{
  "name": "default",
  "sections": [
    { "id": "user_story", "heading": null, "field": "user_story", "style": "user-story", "types": ["story"] },
    { "id": "context", "heading": "Context", "field": "context", "style": "paragraph", "types": ["story", "bug", "spike", "epic"] },
    { "id": "bug", "heading": "Bug details", "field": "bug", "style": "bug", "types": ["bug"] },
    { "id": "spike", "heading": "Spike", "field": "spike", "style": "spike", "types": ["spike"] },
    { "id": "epic", "heading": "Goal and children", "field": "epic", "style": "epic", "types": ["epic"] },
    { "id": "acceptance_criteria", "heading": "Acceptance criteria", "field": "acceptance_criteria", "style": "gwt", "types": ["story", "bug", "spike", "epic"] },
    { "id": "tech_notes", "heading": "Technical notes", "field": "tech_notes", "style": "bullets", "types": ["story", "bug", "spike"] },
    { "id": "api_impact", "heading": "API impact", "field": "api_impact", "style": "api", "types": ["story", "bug"] },
    { "id": "out_of_scope", "heading": "Out of scope", "field": "out_of_scope", "style": "bullets", "types": ["story", "bug", "spike", "epic"] },
    { "id": "dependencies", "heading": "Dependencies", "field": "dependencies", "style": "deps", "types": ["story", "bug", "spike", "epic"] },
    { "id": "refines", "heading": "Changes from the original ticket", "field": "refines", "style": "refines", "types": ["story", "bug", "spike"] }
  ],
  "custom_sections": [],
  "definition_of_ready": [
    { "id": "DOR1", "text": "The user story names a real role, capability and benefit", "check": "auto:user_story" },
    { "id": "DOR2", "text": "At least two Given/When/Then ACs (one for a spike)", "check": "auto:ac_count" },
    { "id": "DOR3", "text": "Every API change names a contract operation", "check": "auto:api_refs" },
    { "id": "DOR4", "text": "Every source reference exists", "check": "auto:sources_exist" },
    { "id": "DOR5", "text": "No open questions", "check": "auto:no_open_questions" },
    { "id": "DOR6", "text": "Dependencies are listed or explicitly none", "check": "review" },
    { "id": "DOR7", "text": "Small enough for one sprint, judged without an estimate", "check": "review" }
  ]
}
```

- **Styles:** `paragraph`, `bullets`, `user-story`, `gwt`, `api`, `deps`, `bug`, `spike`, `epic`, `refines`.
- **Custom sections:** a custom section is `{ "id": "nfr", "heading": "Non-functional requirements", "style": "bullets", "types": ["story"], "required": true }` and reads `story.extra.nfr`.
- **Auto checks:** these are implemented in `sflib/checks.py`. An unknown `auto:` name is reported as `SKIPPED (unknown check)`.
- **Required sections:** a section is required when its field is required by the schema, or when it has `"required": true`. The `sections` list only governs rendering and those `required: true` checks.

## 11. Renderer interface

```python
# scripts/sflib/renderers/<name>.py
FORMAT = "md"        # value for --format
EXTENSION = ".md"    # output is <job>/story<EXTENSION>
def render(story: dict, template: dict) -> str: ...
```

- **Discovery:** the registry finds modules in the package with `pkgutil`.
- **Command:** `python3 scripts/sf.py render <job-id|path/to/story.json> [--format md] [--out PATH]`. It also sets `job.json.title` when given a job id.
- **The markdown renderer is "Jira-paste-safe".** It uses no tables, task-list checkboxes, nested lists or raw HTML. It renders:
  - the title as `#`
  - a bold metadata line
  - headings as `##`
  - flat `-` lists
  - each AC as a bold `AC1 — title` paragraph followed by flat `- **Given** …`, `- **When** …`, `- **Then** …` and `- **And** …` bullets
- Future formats: `jira-wiki` (Server/DC wiki markup) and `adf` (Atlassian Document Format). Neither is in v1.

## 12. `pull-jira-ticket` stub contract

The owner supplies the real skill, `pull-jira-ticket`. The factory depends only on this contract:
- **Invocation:** `pull-jira-ticket <ISSUE-KEY>`, where the key matches `^[A-Z][A-Z0-9_]+-[0-9]+$`. It is read-only.
- **Output:** the issue as JSON, preferably in the shape below, or as markdown. The orchestrator saves the text unchanged to `context/jira/<KEY>.json` if it parses as JSON, otherwise to `<KEY>.md`.
- **Failure:** text starting with `ERROR:`. The orchestrator then runs `sf.py escalate <id> --why "Jira pull failed for <KEY>: <text>"`.
- **Skill name:** comes from `config.jira.skill`. Tests use `pull-jira-ticket-stub` (a different name, so there is no precedence clash with the real skill). The stub runs `python3 scripts/jira_stub.py <KEY> [--format json|md]`, which reads `$STORY_FACTORY_JIRA_FIXTURES/<KEY>.json` (default `tests/fixtures/jira`), and exits 2 with `ERROR: <KEY> not found` when the fixture is missing.

Preferred ticket JSON (`schemas/jira-ticket.schema.json`, not enforced; extra fields are allowed):

```json
{ "key": "DEMO-101", "issue_type": "Story", "summary": "Statement filter", "status": "To Do",
  "description": "Users want to filter statements. Should work for any dates.",
  "acceptance_criteria": null, "labels": ["statements"], "components": ["accounts-api"],
  "parent_key": "DEMO-100", "links": [{ "relation": "relates to", "key": "DEMO-102" }],
  "subtasks": [], "fix_versions": [], "updated": "2026-10-01" }
```

`sf.py jira-keys <id>` prints the keys still to pull, one per line. It collects:
- keys found in the idea text and `jira_key`;
- `parent_key` and `links[].key` from pulled JSON tickets, up to `config.jira.follow_links` hops (default 1) and `config.jira.max_tickets` (default 8).

## 13. Config (`factory.config.json`, gitignored)

```json
{
  "jira": { "skill": "pull-jira-ticket", "project_key": "ABC", "follow_links": 1, "max_tickets": 8 },
  "repos": [ { "name": "accounts-api", "path": "/Users/me/work/accounts-api", "openapi": ["openapi.json"], "docs": ["docs"], "notes": "LoopBack 4 service" } ],
  "team_docs": [ { "name": "team-docs", "path": "/Users/me/work/team-handbook" } ],
  "deny_read": [],
  "template": "default",
  "escalation": { "always_human": ["pii", "auth", "payments", "audit", "regulatory", "data-migration", "breaking-contract", "third-party", "product-decision"], "extra_terms": [] }
}
```

- `STORY_FACTORY_CONFIG` overrides the path. Relative paths resolve against the factory root.
- `sf.py settings` writes `.claude/settings.local.json` with:
  - `permissions.additionalDirectories`: every repo and team-docs path;
  - `permissions.deny`: `Edit(//<path>/**)` for each of them, plus `Read(//<path>/**)` for each `deny_read` entry.
- Settings-file additional directories grant file access only and do not load the team repos' `.claude/` config, which `--add-dir` would.

## 14. Dashboard

- `factory/dashboard.html` is one self-contained file modelled on the reference board. It shares no code with it, because the reference repo has no licence.
- It is served by `python3 scripts/sf.py dashboard [--port 8765]`, which binds 127.0.0.1 only. The reference's `python3 -m http.server` binds all interfaces by default.
- It polls `jobs/` every 2 s.
- The columns are Intake, Draft, Review, Approve, Children, Ready and Needs human.
- Each card shows the type badge, a refine or lite marker, the parent epic, flags, and one chip row per round (`inv ac tech sec`).
- The drawer lists the job's files:
  - `story.md` is rendered and has a Copy button;
  - `.json` files are pretty-printed;
  - reviews are toned by verdict.
- A CSP meta tag (`default-src 'none'; connect-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'`) and the absence of any external URL keep it network-free beyond localhost.

## 15. Copilot lite

`.github/prompts/story-lite.prompt.md` is invoked as `/story-lite …` in VS Code Copilot agent mode (`agent: agent`; tools `read`, `search`, `edit`, `execute`).

How it works:
- It runs the same steps in sequence in one context.
- It plays each role by reading the matching `.claude/agents/*.md` body, so there is one source of truth.
- It writes the same files through the same `sf.py` commands, with `harness: copilot-lite`.
- Reviews run in the order security, tech, ac, invest, and each is written before the next role file is read.
- It cannot rely on invoking the Jira skill. If `context/jira/<KEY>.*` is missing, it stops and asks the owner to run their skill and save the output there, then `/story-lite resume <id>`.
- For epics it drafts and reviews the breakdown, spawns child jobs, and stops. The owner runs `/story-lite resume <child-id>` for each child.

## 16. What differs from the reference repo, and why

| Reference | story-factory | Why |
|---|---|---|
| spec-writer + builder | one `story-writer` | the spec is the product |
| code on a branch in a git worktree, merge to main | `story.json` in a job folder; no worktree, merge or push | team repos are only read; Jira is read-only by decision |
| security, ux, ui and code reviewers | invest, ac, tech and security (bank lens) | owner decision |
| builder resumed up to twice (3 rounds) | writer revises once (2 rounds) | owner decision |
| APPROVE merges, ESCALATE goes to a human | READY means paste by hand; NEEDS-HUMAN carries the exact questions; `/story approve` is the human sign-off | nothing to merge |
| LLM-only gates | `sf.py validate`, `checks` and `gate` add a deterministic floor | a bank wants escalation that cannot be argued away; the schema makes it checkable |
| context read freely | orchestrator pre-pulls Jira into files; agents have no Bash or web; team repos are Edit-denied | read-only guarantee and prompt-injection blast radius |
| markdown artefacts | JSON artefact plus pluggable renderers and templates | owner decision; future formats |
| `http.server` on all interfaces, `cd factory` | 127.0.0.1-only server, CSP, copy button | bank laptop |
| no epics, no lite | epics as parent and children jobs; Copilot lite prompt | owner decisions |
| backlog committed | backlog and config gitignored; `.example` files committed | no work data in a personal repo |
| — | `/story resume`, `/story render` | crash recovery and epic children; re-rendering after hand edits |

## 17. Risks

1. **Escalation fatigue.** Decision 0057 limits blocking to flags the security reviewer raises, so benign stories can reach READY. The risk moves to that reviewer: if it under-flags, a sensitive story is READY. Open questions and assumptions travel with READY stories in the markdown, so the team sees them.
2. **Invented code or API facts.** Mitigated by mandatory `sources`, the existence checks in `checks.md`, and the tech reviewer re-checking refs. This is still weakest for behaviour that is not visible in code.
3. **Work data leaking into the personal repo.** Mitigated by gitignore, the pre-commit hook, `sf.py doctor`, and the rule that fixtures are dummy only. The risk is still real if someone `git add -f`s.
4. **Prompt injection from ticket or code text.** Agents treat context as data; they have no Bash or web, they write one file each, and team repos are Edit-denied. This is not OS-level enforcement: a Python script could still write anywhere, and only the sandbox would stop it.
5. **The orchestrator copies large Jira output verbatim.** It is slow and error-prone. If the owner's skill can write to a path, add `jira.writes_to_path` later.
6. **Copilot lite reviews are same-context**, so they are less independent. The dashboard marks lite jobs. VS Code's `runSubagent` could add isolation later, but that is out of scope for v1.
7. **Unverified platform facts.** These are listed in the sources section below. The most important is whether Jira Cloud converts pasted markdown, which needs a manual test on the work Jira.
8. **Claude Code drift.** If resuming the writer by `SendMessage` fails, the fallback is a fresh writer that reads `story.json` and the round folder, which works because all state is in files.
9. **Cost and time.** One job is about six agent runs; an epic with three children is about 24. Children run sequentially.

## 18. Open questions for the owner (AskUserQuestion-ready)

1. **Bank flags.** Decided 2026-10-13 (decision 0057): option (c), only flags raised by the security reviewer force it.
   - (a) Any flag → NEEDS-HUMAN.
   - (b) Only pii, auth, payments and regulatory force it; the others are just noted.
   - (c) Only flags raised by the security reviewer force it.
2. **Jira fields.** Which extra Jira fields should `story.json` carry beyond labels, components, parent and links? (multi-select)
   - (a) None.
   - (b) Priority.
   - (c) Fix version.
   - (d) Team custom fields through template `extra`.
3. **`pull-jira-ticket` output.** What does your skill return?
   - (a) Raw Jira REST JSON (`fields.*`), so the factory needs an adapter.
   - (b) JSON in the factory's preferred shape.
   - (c) Markdown.
   - (d) Not sure yet; keep the stub flexible.
4. **Epic children.** How should children run after the breakdown is READY?
   - (a) Sequentially in the same session (current).
   - (b) Stop after the breakdown; run each child with `/story resume`.
   - (c) Children in parallel, one session each.

## Sources (checked 2026-10-13)

Verified:
- Reference repo, read through `gh api`: github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code. The repo has no licence file, so no code is copied.
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
  - Frontmatter: `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `isolation`, and others.
  - Resume with `SendMessage` to the agent ID or name. Resumed agents keep their full history.
  - The default limit is 20 concurrent subagents.
- Claude Code skills: https://code.claude.com/docs/en/skills
  - `$ARGUMENTS`, `$0`/`$1`, `argument-hint`, `disable-model-invocation`, `allowed-tools`, `context: fork`.
  - Commands are merged into skills.
- Claude Code permissions: https://code.claude.com/docs/en/permissions
  - `Edit(//abs/**)` syntax, and Edit rules cover Write.
  - `additionalDirectories` in settings grants file access only, while `--add-dir` also loads that directory's skills and agents.
  - Deny rules don't stop arbitrary subprocesses.
- VS Code prompt files: https://code.visualstudio.com/docs/copilot/customization/prompt-files
  - `.github/prompts/*.prompt.md`; frontmatter `description`, `name`, `argument-hint`, `agent`, `model`, `tools`.
  - Invoked with `/name args`.
- VS Code custom agents: https://code.visualstudio.com/docs/copilot/customization/custom-agents
  - `.github/agents`; custom agents are the renamed chat modes.
  - It also reads Claude-format agents in `.claude/agents`.
- VS Code subagents: https://code.visualstudio.com/docs/copilot/agents/subagents
  - Uses the `runSubagent` tool, and prompt files can add the `agent` tool set.
  - The page does not say whether subagents run in parallel.
- VS Code tools reference: https://code.visualstudio.com/docs/agents/reference/tools-reference
  - Tool sets `read`, `search`, `edit`, `execute`, `agent`.
- VS Code agent skills: https://code.visualstudio.com/docs/copilot/customization/agent-skills
  - Reads `.claude/skills` and `~/.claude/skills`; skills show as slash commands.
- VS Code custom instructions: https://code.visualstudio.com/docs/copilot/customization/custom-instructions
  - AGENTS.md is supported and controlled by `chat.useAgentsMdFile`.
- Atlassian: https://confluence.atlassian.com/jirasoftware/markdown-formatting-in-jira-cloud-1528533331.html
  - Headings, lists, bold, code, links and quotes convert.
  - `*` markers don't make nested lists.
  - Task lists and tables are not listed.

Not verified:
- Whether `chat.useAgentsMdFile` is on by default. The lite prompt reads AGENTS.md explicitly anyway.
- Whether prompt-file `tools` accepts the tool-set names, which the reference lists for the `#` picker.
- Whether pasting, as opposed to typing, markdown converts in the current Jira Cloud editor. Atlassian's pages disagree; test it on the work Jira.
- Whether subagents inherit `additionalDirectories`. The design assumes they do; step 04 tests it.
- Whether a prompt file can invoke a skill. Lite does not rely on it.
