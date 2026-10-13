# API guidelines

- Errors use `{ "error": { "code": "UPPER_SNAKE", "message": "..." } }`.
- Another customer's resource returns 404, not 403.
- Dates are ISO 8601 with `format: date`.
- List endpoints return `{ "items": [...] }`.
