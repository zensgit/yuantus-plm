# Verification — Document Sync BasicAuth Outbound HTTP Mirror Probe

## Date

2026-04-07

## Scope

Implementation of `POST /api/v1/document-sync/sites/{site_id}/mirror-probe`
backed by `DocumentSyncService.mirror_probe(site_id)`.

Design doc: `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md`.

## What was implemented

1. `DocumentSyncService.mirror_probe(site_id)` — service method that:
   - Loads the site, validates `base_url`, `auth_type=="basic"`, and the
     basic auth contract (non-empty username + password).
   - Issues a single `httpx.Client.get(...)` with `httpx.BasicAuth(...)` and
     a 10s timeout against `{base_url.rstrip('/')}/api/v1/document-sync/overview`.
   - Maps every failure (missing site, missing base_url, missing auth contract,
     `httpx.RequestError`, 401/403, non-JSON 2xx body) to `ValueError`.
   - Never echoes the password in any error message or return payload.
2. `POST /document-sync/sites/{site_id}/mirror-probe` router endpoint that
   wraps the service in the standard `try/except ValueError → 400` pattern.
3. Tests: 9 service tests (`TestMirrorProbe`) + 2 router tests.

## Test results

```
$ .venv/bin/python3 -m pytest -q \
    src/yuantus/meta_engine/tests/test_document_sync_service.py \
    src/yuantus/meta_engine/tests/test_document_sync_router.py \
    -k "mirror_probe or MirrorProbe"
...........                                                              [100%]
11 passed, 152 deselected in 3.65s
```

Full document_sync service + router suite (regression):

```
$ .venv/bin/python3 -m pytest -q \
    src/yuantus/meta_engine/tests/test_document_sync_service.py \
    src/yuantus/meta_engine/tests/test_document_sync_router.py
163 passed in 1.53s
```

`py_compile`:

```
$ .venv/bin/python3 -m py_compile \
    src/yuantus/meta_engine/document_sync/service.py \
    src/yuantus/meta_engine/web/document_sync_router.py \
    src/yuantus/meta_engine/tests/test_document_sync_service.py \
    src/yuantus/meta_engine/tests/test_document_sync_router.py
py_compile ok
```

`git diff --check`: clean.

## Service test coverage (`TestMirrorProbe`)

| Test | Validates |
|------|-----------|
| `test_mirror_probe_success_returns_remote_overview` | 200 + JSON dict body → `ok=True`, `remote_overview` populated, `httpx.BasicAuth` passed, password not echoed |
| `test_mirror_probe_missing_site_raises` | `session.get → None` → `ValueError("not found")` |
| `test_mirror_probe_missing_base_url_raises` | empty `base_url` → `ValueError("no base_url")` |
| `test_mirror_probe_missing_basic_auth_contract_raises` | `auth_type=None` → `ValueError("auth_type='basic'")` |
| `test_mirror_probe_basic_auth_missing_password_raises` | empty password → `ValueError("missing username or password")` |
| `test_mirror_probe_401_maps_to_value_error` | 401 → `ValueError("rejected by remote (401)")` |
| `test_mirror_probe_403_maps_to_value_error` | 403 → `ValueError("rejected by remote (403)")` |
| `test_mirror_probe_request_error_maps_to_value_error` | `httpx.ConnectError` → `ValueError("failed: ConnectError")` |
| `test_mirror_probe_non_json_2xx_body_maps_to_value_error` | 200 + `response.json()` raises → `ValueError("non-JSON 2xx body")` |

## Router test coverage

| Test | Validates |
|------|-----------|
| `test_mirror_probe_site_success` | 200 path-through, body fields preserved (`ok`, `site_id`, `endpoint`, `status_code`, `remote_overview`) |
| `test_mirror_probe_site_value_error_maps_to_http_400` | service `ValueError` → `HTTPException(400)` with detail surfaced |

## Mocking strategy

- `httpx.Client` is patched at the module level used by the service
  (`patch("httpx.Client", return_value=fake_client)`); a `_FakeClientCM`
  context-manager helper is reused across the success / status-code / error
  cases.
- `_FakeProbeResponse` provides a `.json()` that can either return a payload
  or raise `ValueError` (matches `httpx.Response.json()`'s real failure mode
  when the body is not JSON).
- The router tests patch `DocumentSyncService` directly, so they exercise the
  `try/except ValueError → 400` mapping without needing httpx at all.

## Non-leak verification

`test_mirror_probe_success_returns_remote_overview` performs a hard
`assert "secret" not in str(result)` after a successful probe with a fake
password of `"secret"`. This guarantees the password does not appear in any
field of the success response.

For failure paths the password is never substituted into any error message
(by code inspection — every `raise ValueError(...)` uses only `site_id`,
`endpoint`, status code, or exception class name).

## Closure

- 11 new tests, 0 failures.
- 152 unrelated document_sync tests still pass (163 total in scope).
- No new database migration; no new schema field.
- No change to existing site / list / get masked-auth-config contract.
- No known blocking gaps for this minimal probe surface.
