# Verification — Document Sync BasicAuth HTTP Mirror Execute + Job Mapping

## Date

2026-04-07

## Scope

Implementation of `POST /api/v1/document-sync/sites/{site_id}/mirror-execute`
backed by `DocumentSyncService.mirror_execute(site_id)`. Persists the remote
overview outcome as a local `SyncJob` (`completed` on success, `failed` on
remote-side error) and returns a uniform JSON contract.

Design doc: `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md`.

## What was implemented

1. `DocumentSyncService.mirror_execute(site_id)` — service method that:
   - Pre-validates site existence, `base_url`, `auth_type=='basic'`, and the
     basic auth contract (raises `ValueError` if any check fails — no job is
     created in this case).
   - Creates a `SyncJob` via the existing `create_job(site_id, direction)`
     and transitions it through `pending → running`.
   - Calls `httpx.Client.get(...)` with `httpx.BasicAuth` against
     `{base_url.rstrip('/')}/api/v1/document-sync/overview`, 10 s timeout.
   - Classifies the outcome:
     - `httpx.RequestError` → `request failed: <type>`
     - 401 / 403 → `rejected by remote (4xx)`
     - 2xx + dict JSON → success, payload captured as `remote_overview`
     - 2xx + non-JSON or non-dict → `non-JSON 2xx body` / `non-dict 2xx body`
     - other non-2xx → `remote status <code>`
   - On success: maps `remote.total_jobs / total_conflicts / total_errors`
     onto `job.total_documents / conflict_count / error_count`, derives
     `synced_count`, stores `remote_overview` in `job.properties`, and
     transitions to `completed`.
   - On any failure: stores the error detail in `job.properties.mirror_error`
     and transitions to `failed`. **Does not raise.**
   - Returns a uniform dict: `ok`, `job_id`, `site_id`, `state`, `endpoint`,
     `status_code`, `summary`.
2. `POST /document-sync/sites/{site_id}/mirror-execute` router endpoint that
   wraps the service in the standard `try/except ValueError → 400` pattern,
   commits on success, rolls back on `ValueError`.
3. Tests: 8 service tests (`TestMirrorExecute`) + 2 router tests.

## Mirror execute supports

- BasicAuth outbound HTTP execute against a configured site
- Local SyncJob lifecycle: `pending → running → completed | failed`
- Remote payload mapping onto `total_documents / synced_count /
  conflict_count / error_count`
- Failure containment: 5 distinct remote-side error classes all collapse to
  a `failed` SyncJob with a structured `mirror_error` string in
  `job.properties`
- Pre-job stable error mapping (5 distinct `ValueError` causes → HTTP 400)
- Password non-leak (verified by explicit assertion)
- DB rollback on pre-job failure / commit on success

## Test commands and results

### 1. Filtered pytest (request command #3)

```
$ .venv/bin/python3 -m pytest -q \
    src/yuantus/meta_engine/tests/test_document_sync_service.py \
    src/yuantus/meta_engine/tests/test_document_sync_router.py \
    -k 'mirror_execute or mirror_probe or site or auth'
........................................................................ [ 90%]
........                                                                 [100%]
80 passed, 95 deselected in 2.09s
```

> Note: `80` reflects the follow-up package
> `document-sync-basic-auth-http-mirror-execute-and-job-mapping-coverage-followup`,
> which added two focused failure-branch tests (`non-dict 2xx` and
> `generic non-2xx`). The original execute package landed `78` filtered
> tests; the follow-up bumps that to `80` without changing any production
> semantics.

### 2. Full document_sync regression (no scope creep, no flakes)

```
$ .venv/bin/python3 -m pytest -q \
    src/yuantus/meta_engine/tests/test_document_sync_service.py \
    src/yuantus/meta_engine/tests/test_document_sync_router.py
........................................................................ [ 41%]
........................................................................ [ 83%]
.............................                                            [100%]
173 passed in 1.05s
```

### 3. py_compile (request command #4)

```
$ PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/python3 -m py_compile \
    src/yuantus/meta_engine/document_sync/service.py \
    src/yuantus/meta_engine/web/document_sync_router.py \
    src/yuantus/meta_engine/tests/test_document_sync_service.py \
    src/yuantus/meta_engine/tests/test_document_sync_router.py
py_compile ok
```

### 4. git diff --check (request command #5)

```
$ git diff --check
git diff --check clean
```

## Service test coverage (`TestMirrorExecute`)

| Test | Validates |
|------|-----------|
| `test_mirror_execute_success_creates_completed_job` | 200 + dict JSON → `state=completed`, aggregates mapped (`total_documents=12`, `conflict_count=2`, `error_count=1`, `synced_count=9`), `job.properties` contains `mirror_endpoint / mirror_status_code / remote_overview`, no `mirror_error`, password not echoed |
| `test_mirror_execute_request_error_marks_job_failed` | `httpx.ConnectError` → `state=failed`, `status_code=None`, `mirror_error` contains `ConnectError`; SyncJob is still created and persisted |
| `test_mirror_execute_401_marks_job_failed` | 401 → `state=failed`, `status_code=401`, `mirror_error` contains `401` |
| `test_mirror_execute_403_marks_job_failed` | 403 → `state=failed`, `status_code=403`, `mirror_error` contains `403` |
| `test_mirror_execute_non_json_2xx_marks_job_failed` | 200 + `response.json()` raises → `state=failed`, `mirror_error == "non-JSON 2xx body"` |
| `test_mirror_execute_non_dict_2xx_marks_job_failed` | 200 + JSON list (not dict) → `state=failed`, `mirror_error == "non-dict 2xx body"`, `remote_overview is None` (added by follow-up) |
| `test_mirror_execute_generic_non_2xx_marks_job_failed` | 500 (not 401/403, not 2xx) → `state=failed`, `status_code=500`, `mirror_error == "remote status 500"` (added by follow-up) |
| `test_mirror_execute_missing_site_raises_before_job` | `session.get → None` → `ValueError("not found")`, **no SyncJob created** |
| `test_mirror_execute_missing_base_url_raises_before_job` | empty `base_url` → `ValueError("no base_url")`, no SyncJob created |
| `test_mirror_execute_missing_basic_auth_contract_raises_before_job` | `auth_type=None` → `ValueError("auth_type='basic'")`, no SyncJob created |

## Router test coverage

| Test | Validates |
|------|-----------|
| `test_mirror_execute_site_success` | 200 path-through, body fields preserved (`ok`, `job_id`, `site_id`, `state`, `endpoint`, `status_code`, `summary.*`), `db.commit` called |
| `test_mirror_execute_site_value_error_maps_to_http_400` | service `ValueError` → `HTTPException(400)` with detail surfaced, `db.rollback` called |

## Mocking strategy

The service tests use a session helper `_execute_session(site)` that
dispatches `session.get` on model class:

```python
def _get(model, _id):
    if model is SyncSite:
        return site
    if model is SyncJob:
        for obj in reversed(session._added):
            if isinstance(obj, SyncJob):
                return obj
        return None
session.get.side_effect = _get
```

This lets `create_job` (which calls `session.get(SyncSite, ...)`) and
subsequent `transition_job_state` calls (which call
`session.get(SyncJob, job_id)`) cooperate against the same mock without any
real database. The freshly-created `SyncJob` is captured from `session._added`
so each test can also assert on its final aggregated state.

`httpx.Client` is patched module-wide; the same `_FakeClientCM` and
`_FakeProbeResponse` helpers introduced by the mirror probe package are
reused unchanged.

## Non-leak verification

`test_mirror_execute_success_creates_completed_job` performs a hard
`assert "secret" not in str(result)` after a successful execute against a
site whose password is `"secret"`. This guarantees the password does not
appear in any field of the success response.

By code inspection, every `error_detail` string in `mirror_execute` is
constructed from only `endpoint`, `status_code`, an exception class name, or
a fixed literal. No path interpolates the password into a logged or returned
string.

## Closure

- 10 new tests in the original execute package, plus 2 follow-up
  failure-branch tests (`non-dict 2xx body`, `generic non-2xx remote status`),
  for a total of 12 new tests on this contract — 0 failures.
- 80 filtered tests pass against the requested `-k` selector.
- 173 unrelated document_sync tests still pass (full module regression).
- No new database migration; no new schema field.
- No change to existing site / list / get masked-auth-config contract.
- No board / export / readiness layer added.
- No batch, no async refactor.
- No new adapter class.
- No known blocking gaps for this minimal mirror execute surface.
