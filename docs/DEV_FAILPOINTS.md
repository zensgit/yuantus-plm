# Dev Failpoints (Test-Only)

This repo includes **test-only failpoints** to inject controlled failures in release orchestration, so we can reliably cover rollback behavior in E2E tests.

## Enable

Failpoints are disabled by default. Enable them only in test/dev environments:

```bash
export YUANTUS_TEST_FAILPOINTS_ENABLED=true
```

Playwright enables this automatically in `playwright.config.js`.

## Use

Send a header on the release orchestration execute endpoint:

- Header: `x-yuantus-failpoint: <token>`
- Endpoint: `POST /api/v1/release-orchestration/items/{item_id}/execute`

When the token matches the currently executing step, the server raises a `ValueError` and the orchestration run records that step as `failed` (and triggers rollback when `rollback_on_failure=true`).

## Tokens

Tokens are matched exactly against these forms:

- `<kind>:<resource_id>`
- `<resource_type>:<resource_id>`
- `release-orchestration:<kind>:<resource_id>`
- `release-orchestration:<resource_type>:<resource_id>`

Examples:

- `routing_release:<routing_id>`
- `routing:<routing_id>`
- `mbom_release:<mbom_id>`
- `baseline_release:<baseline_id>`

## Safety Notes

- Failpoints only work when `YUANTUS_TEST_FAILPOINTS_ENABLED=true`.
- In production deployments this should remain `false`.

