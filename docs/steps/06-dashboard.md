---
tags: [project, story-factory, build-step]
created: 2026-10-13
---

# Step 06: local HTML dashboard

Part of [story-factory](../../README.md); the architecture is in [design](../design.md). This note stands alone.

## Purpose

Build a single-file dashboard that shows every job as a card moving across the stages, with review chips filling in as verdicts land. It is modelled on zazencodes' software-factory dashboard: dark board, 2 s polling, and directory listings read from `http.server`.

Write it from scratch: the reference repo has no licence. It must run with no network beyond localhost, because it will run on a bank laptop.

## Background you need

- Repo `~/Documents/ai/story-factory`. Jobs live in `factory/jobs/<id>/`.
- `job.json` example:

```json
{ "id": "004-refine-demo-101", "type": "story", "mode": "refine", "harness": "claude", "idea": "refine DEMO-101",
  "jira_key": "DEMO-101", "parent": null, "children": {}, "title": "Filter account statements by date range",
  "stage": "review", "round": 2, "revisions_used": 1,
  "reviews": { "invest": "PASS", "ac": "PASS", "tech": "pending", "security": "CHANGES" },
  "flags": ["pii"], "decision": null, "approved_by": null, "gate_reasons": [], "writer_agent": "a1b2",
  "created": "2026-10-13T09:00:00Z", "updated": "2026-10-13T09:12:41Z" }
```

- Stages, in column order: `intake`, `draft`, `review`, `approve`, `children` (epics only), `ready`, `needs-human`.
- Lenses and chip labels: `invest`→`inv`, `ac`→`ac`, `tech`→`tech`, `security`→`sec`.
- Job files:
  - `brief.md`, `story.json`, `story.md`, `decision.md`, `rework-<k>.md`
  - `context/jira/*.json|.md`
  - `round-<N>/{story.json,checks.md,review-<lens>.md}`
- First lines: reviews `VERDICT: PASS|CHANGES`; decisions `READY|NEEDS-HUMAN`. The second line of both is `FLAGS: …`.

## Prerequisites

- Step 01 is done (`sf.py` exists). No other step is needed: the test generates fake jobs.

## Files to create

```
factory/dashboard.html
scripts/sflib/server.py            (sf.py dashboard)
tests/make_demo_jobs.py            (writes fake jobs in every stage into a given dir)
tests/test_dashboard.py
```

## Interfaces

### `python3 scripts/sf.py dashboard [--port 8765]`

- Serves `factory/` with `http.server.ThreadingHTTPServer` and `SimpleHTTPRequestHandler`, using `functools.partial(..., directory=<root>/factory)`.
- Binds **127.0.0.1 only**, never `0.0.0.0`.
- Sends `Cache-Control: no-store` on every response.
- `--jobs-dir DIR` (for tests) serves a temp dir that contains a copy of `dashboard.html` and a `jobs/` folder.
- Prints `Dashboard: http://127.0.0.1:<port>/dashboard.html`.

### `factory/dashboard.html` requirements

- **Self-contained.** No external URL anywhere: no fonts, CDNs or analytics. Use system fonts.
- **CSP meta**, in `<head>`: `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'">`.
- **Job list.** Fetch `jobs/` (the `http.server` HTML index), parse the `<a href>` entries ending in `/` with `DOMParser`, then fetch each `jobs/<id>/job.json`. Poll every 2000 ms. A failed fetch shows a status line, not a crash.
- **Columns.** Show the seven stages with headers and counts. Hide `children` when it is empty. `needs-human` is visually loud, using the accent colour and border.
- **Card contents:**
  - the number and slug;
  - a type badge (story, bug, spike, epic), plus `refine` if `mode` is refine and `lite` if `harness` is `copilot-lite`;
  - the title, or the idea cut to 90 characters;
  - `↑ <parent>` when `parent` is set; for an epic, `children n/m ready`;
  - flag pills;
  - chip rows.
- **Chip rows.** One row per round, `R1`, `R2`. The current round comes from `job.reviews`. Earlier rounds come from fetching the first line of `round-<n>/review-<lens>.md`, cached once a round is finished. Chip states:
  - PASS: green;
  - CHANGES: amber;
  - pending: grey, pulsing while `stage == review`;
  - missing or invalid: red with `?`.
- **Escaping.** Every string from a file goes through an `esc()` HTML-escaper before `innerHTML`. Links are only `http(s)`, relative or `#`, with `rel="noopener"`.
- **Drawer.** Clicking a card opens a right-hand drawer.
  - Header: the id, stage, round, title, `gate_reasons` if any, and `approved_by`.
  - File list grouped as:
    - Story: `story.md`, `story.json`, `decision.md`, `brief.md`, `rework-*.md`
    - Round N: `checks.md`, the reviews, `story.json`
    - Context: `context/jira/*`
  - Each file gets a coloured dot from its first line. Folder listings are fetched recursively.
  - `.md` files go through a small built-in markdown renderer: headings, paragraphs, flat and nested lists, task boxes, bold, italic, inline code, code fences, blockquotes, simple tables, and the first-line verdict as a coloured pill.
  - `.json` files are pretty-printed in `<pre>` (`JSON.stringify(obj, null, 2)`, escaped).
  - `story.md` gets a **Copy markdown** button: `navigator.clipboard.writeText`, with a fallback that selects a hidden textarea and runs `document.execCommand('copy')`. It shows "Copied" for 1.5 s.
  - Escape or a scrim click closes the drawer.
- **Footer.** Lists the commands: `/story <idea>`, `/story epic <idea|KEY>`, `/story refine <KEY>`, `/story next`, `/story approve <id>`, `/story rework <id> <note>`, `/story resume <id>`, `/story render <id>`.
- **Layout.** It works at 390 px width: columns stack, and the drawer goes full width.

### `tests/make_demo_jobs.py OUT_DIR`

Writes 8 fake jobs with all DEMO data:
- one each in intake, draft, review (round 1, mixed chips), approve, and ready;
- one in review round 2 with round-1 files present;
- one needs-human with flags `pii,auth` and `gate_reasons`;
- one epic in `children` with 2 children (one ready, one draft).

Also copy `factory/dashboard.html` into `OUT_DIR`.

## Acceptance tests

```bash
cd ~/Documents/ai/story-factory
python3 -m unittest discover -s tests -v              # all pass
grep -nE 'https?://' factory/dashboard.html           # → no output (no external URLs)
grep -c 'Content-Security-Policy' factory/dashboard.html   # → 1
D=$(mktemp -d); python3 tests/make_demo_jobs.py $D
python3 scripts/sf.py dashboard --port 8765 --jobs-dir $D &   # → Dashboard: http://127.0.0.1:8765/dashboard.html
sleep 1; lsof -nP -iTCP:8765 -sTCP:LISTEN | grep -c '127.0.0.1:8765'   # → 1  (never *:8765)
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/dashboard.html   # → 200
curl -sI http://127.0.0.1:8765/jobs/ | grep -i cache-control   # → Cache-Control: no-store
kill %1
```

`tests/test_dashboard.py` must:
- start the server on a free port in a thread;
- fetch `dashboard.html`, `jobs/` and one `job.json`;
- assert there are no external URLs and the CSP meta is present;
- assert `esc(` is used in the card template;
- assert all 7 stage keys and all 4 lens keys appear in the script.

If Node is available, extract the `<script>` block and run `node --check` on it; skip that part if Node is missing.

**Manual check.** Open `http://127.0.0.1:8765/dashboard.html` in a browser with the network off (Wi-Fi off). Confirm:
- 8 cards in the right columns;
- the needs-human card stands out;
- the epic shows `children 1/2 ready`;
- the drawer opens `story.md`, and Copy puts markdown on the clipboard;
- `story.json` shows pretty-printed;
- the browser devtools network tab shows only `127.0.0.1` requests;
- it works at phone width.

Then edit one fake `job.json` stage by hand: the card moves within about 2 s.

## Out of scope

- Any action buttons that run commands. The board is read-only, apart from Copy.
- Auth: it is bound to localhost and has no secrets.
- Websockets.
- Any external library.
