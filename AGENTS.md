# AGENTS.md: working on story-factory itself

story-factory is a Claude Code "factory" that writes Jira stories. This file covers
changing the factory, not running it.

## Rules

- Tests: `python3 -m unittest discover -s tests -v`.
- Python 3.9 stdlib only. No pip installs, no network, no `match` statement, and
  use `from __future__ import annotations`.
- The CLI is `python3 scripts/sf.py`. It is a thin dispatcher; each subcommand lives
  in `scripts/sflib/commands/<name>.py` and exposes `register(subparsers)`.
- Never commit anything under `factory/jobs/` (except `.gitkeep`), nor
  `factory/backlog.md`, `factory.config.json` or `templates/local/` (except `.gitkeep`).
- Fixtures are dummy data only, using the project key `DEMO` and the repo name
  `accounts-api`. Never put real bank, customer, employee or work data in this repo.
- Every agent writes exactly one file.
- Install the pre-commit hook with `git config core.hooksPath scripts/hooks`.
