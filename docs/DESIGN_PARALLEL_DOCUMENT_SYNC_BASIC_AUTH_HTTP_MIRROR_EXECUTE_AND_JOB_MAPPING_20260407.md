# Document Sync — BasicAuth HTTP Mirror Execute + Job Mapping (Design)

## Date

2026-04-07

## Goal

Advance the document_sync mirror line from "auth contract + probe" to a
**minimum viable executable mirror adapter**: a single endpoint that issues
a BasicAuth outbound HTTP call to a remote document_sync deployment, maps
the remote overview payload onto a local `SyncJob`, and persists the job
in `completed` or `failed` state.

This is the smallest possible end-to-end execute path. It deliberately uses
the existing remote `overview` endpoint as the read-through target rather
than introducing a dedicated remote execute API on the peer side.

## Non-Goals

- No board / export / readiness surfaces
- No batch execute, no fan-out across multiple sites
- No async / background refactor (call is synchronous)
- No retry / backoff / circuit breaker
- No new auth schemes (still BasicAuth only)
- No fabricated `SyncRecord` rows when remote does not expose per-document detail
- No new database migration
- No new dedicated adapter class
- No change to existing site / list / get masked-auth contract

## Surface

### Endpoint

`POST /api/v1/document-sync/sites/{site_id}/mirror-execute`

- Auth: requires logged-in user (`get_current_user`)
- No request body
- Returns execute outcome JSON
- On success: `db.commit()` runs (the new SyncJob is persisted)
- On pre-job `ValueError`: `db.rollback()` runs and the router maps to HTTP 400

### Success response shape

```json
{
  "ok": true,
  "job_id": "<uuid>",
  "site_id": "site-1",
  "state": "completed",
  "endpoint": "https://hq.example.com/api/v1/document-sync/overview",
  "status_code": 200,
  "summary": {
    "total_documents": 12,
    "synced_count": 9,
    "conflict_count": 2,
    "error_count": 1,
    "remote_overview": { "...": "..." },
    "mirror_error": null
  }
}
```

### Failure response shapes

**Pre-job ValueError → HTTP 400** (no SyncJob is created):

| Cause | Detail substring |
|-------|------------------|
| Site not found | `not found` |
| Site has no `base_url` | `no base_url` |
| Site `auth_type != "basic"` | `auth_type='basic'` |
| Basic auth contract missing username or password | `missing username or password` |
| Site not in `active` state (via `create_job` reuse) | `Cannot create job` |

**Post-job remote-side failure → HTTP 200, `state="failed"`** (the SyncJob
**is** persisted with `state=failed` and the failure detail in
`job.properties.mirror_error`):

| Cause | `mirror_error` value |
|-------|----------------------|
| `httpx.RequestError` (connect/timeout/etc.) | `request failed: <ExcClassName>` |
| Remote 401 | `rejected by remote (401)` |
| Remote 403 | `rejected by remote (403)` |
| Other non-2xx | `remote status <code>` |
| 2xx but body is not JSON | `non-JSON 2xx body` |
| 2xx JSON but not a dict | `non-dict 2xx body` |

## Default remote endpoint

`{base_url.rstrip('/')}/api/v1/document-sync/overview`

Reuses the constant `_MIRROR_PROBE_PATH` introduced by the mirror probe
package, since "execute" in this minimal package is a read-through against
the same overview endpoint.

## Service-side implementation

`DocumentSyncService.mirror_execute(site_id)` in
`src/yuantus/meta_engine/document_sync/service.py`:

1. **Pre-validation** (raise `ValueError`):
   - `get_site(site_id)` returns non-None
   - `site.base_url` non-empty
   - `site.auth_type == "basic"`
   - `site.auth_config` has non-empty username + password
2. **Job creation** — reuse existing helpers:
   - `self.create_job(site_id=site_id, direction=site.direction)` →
     `SyncJob` in `pending` state. (`create_job` itself enforces site-active
     and direction validity, so any failure here is also `ValueError →
     HTTP 400`.)
   - `self.transition_job_state(job.id, RUNNING)`
3. **Outbound call**:
   ```python
   with httpx.Client(timeout=_MIRROR_PROBE_TIMEOUT_S) as client:
       response = client.get(endpoint, auth=httpx.BasicAuth(username, password))
   ```
4. **Outcome classification**:
   - `httpx.RequestError` → `error_detail = "request failed: <type>"`
   - `401 / 403` → `error_detail = "rejected by remote (401|403)"`
   - 2xx + dict JSON → `remote_overview = payload`
   - 2xx + non-JSON → `error_detail = "non-JSON 2xx body"`
   - 2xx + non-dict JSON → `error_detail = "non-dict 2xx body"`
   - other non-2xx → `error_detail = "remote status <code>"`
5. **Job mapping**:
   - On success (`remote_overview` present, no `error_detail`):
     - `job.total_documents = int(remote.total_jobs or 0)`
     - `job.conflict_count = int(remote.total_conflicts or 0)`
     - `job.error_count = int(remote.total_errors or 0)`
     - `job.synced_count = max(total_documents - conflicts - errors, 0)`
     - `job.properties = {mirror_endpoint, mirror_status_code, remote_overview}`
     - `transition_job_state(job.id, COMPLETED)`
   - On any failure:
     - `job.properties = {mirror_endpoint, mirror_status_code, remote_overview,
       mirror_error}`
     - `transition_job_state(job.id, FAILED)`
6. **Return** the success-response shape above.

### Why we use `create_job` instead of constructing a `SyncJob` directly

`create_job` already encapsulates the site-active check, direction
validation, and ID/state defaults. Reusing it keeps the implementation
minimal and prevents this package from becoming a parallel job-construction
path.

### Why we route through `RUNNING`

`_JOB_TRANSITIONS` only allows `pending → running → completed|failed`. We
must transition through `RUNNING` to reach a terminal state legally. This
also makes the lifecycle observable to anyone watching `jobs_by_state`.

### Why we use `total_jobs` from the remote overview as `total_documents`

The remote `overview` payload does not expose per-document counts. The
closest aggregate is `total_jobs` (total sync jobs the peer has run).
Treating each remote job as a unit of work for the local mirror job is the
most defensible mapping that:

- preserves a non-zero meaningful value when the remote is healthy
- naturally derives `synced_count` as `total - conflicts - errors`
- requires no fabricated `SyncRecord` rows

If the peer ever exposes a real document-count field, mapping can be
updated trivially.

## Router-side implementation

`POST /document-sync/sites/{site_id}/mirror-execute` in
`src/yuantus/meta_engine/web/document_sync_router.py`:

```python
@document_sync_router.post("/sites/{site_id}/mirror-execute")
def mirror_execute_site(site_id, db, user):
    service = DocumentSyncService(db)
    try:
        result = service.mirror_execute(site_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return result
```

This mirrors the existing write-endpoint convention (e.g., `create_site`,
`create_job`): commit on success, rollback + 400 on `ValueError`. Note that
remote-side failures do **not** raise — they end up as a persisted `failed`
SyncJob, so the success path runs `db.commit()` even when `ok` is `False`.

## Why this is safe

- **Password never echoed**: read from `site.auth_config`, used only in
  `httpx.BasicAuth(...)`. Never appears in any error message, log line,
  job property, or response field. Verified by an explicit
  `"secret" not in str(result)` assertion in the success test.
- **Bounded blast radius**: single GET against a hard-coded path with a
  10s timeout, no retry loop.
- **Failure containment**: a remote error never raises 500. The router
  always sees either (a) a clean success/failed dict or (b) a pre-job
  `ValueError` for which it returns 400. No exception escapes uncaught.
- **No new schema**: persistence reuses the existing `SyncJob` row, with
  failure detail living inside the existing `properties` JSON column.
- **Pre-job validation does not write rows**: missing site / base_url /
  auth raise before `create_job` is called, so no orphan jobs are produced
  for invalid configurations.

## Test plan

See `DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md`.

## Files touched

- `src/yuantus/meta_engine/document_sync/service.py` — new `mirror_execute` method
- `src/yuantus/meta_engine/web/document_sync_router.py` — new endpoint
- `src/yuantus/meta_engine/tests/test_document_sync_service.py` — `TestMirrorExecute`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py` — 2 router tests
- `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md` (this doc)
- `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md`
- `docs/DELIVERY_DOC_INDEX.md`
