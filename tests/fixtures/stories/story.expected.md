# Filter account statements by date range

**Type:** Story · **Jira:** DEMO-101 (refined) · **Parent:** DEMO-100 · **Components:** accounts-api

**As a** retail banking customer, **I want** to list my statements for a date range, **so that** I can find last quarter's statements without paging through all of them.

## Context

Statements are served by `StatementController.find` at `GET /accounts/{accountId}/statements`, which returns every statement for the account, newest first.

## Acceptance criteria

**AC1 — happy**

- **Given** account A has statements dated 2026-01-31, 2026-02-28 and 2026-03-31
- **When** its owner calls GET /accounts/A/statements?from=2026-02-01&to=2026-03-31
- **Then** the response is 200 with exactly the 2026-02-28 and 2026-03-31 statements, newest first

**AC2 — error**

- **Given** any account owned by the caller
- **When** the caller sends a from date later than the to date
- **Then** the response is 400 with error code INVALID_DATE_RANGE

**AC3 — security**

- **Given** account B belongs to another customer
- **When** the caller requests GET /accounts/B/statements?from=2026-01-01&to=2026-03-31
- **Then** the response is 404, the same as without the filter

## Technical notes

- Filter in the repository query, not in memory.
- Dates are inclusive calendar dates.

## API impact

- `GET /accounts/{accountId}/statements` (accounts-api:openapi.json): modify — Add optional query parameters from and to (format: date). Breaking: no.

## Out of scope

- Filtering by amount or statement type
- Mobile app UI

## Dependencies

- None.

## Changes from the original ticket

- acceptance_criteria: Replaced 'works for any dates' with three Given/When/Then criteria (The original criterion was not testable)
