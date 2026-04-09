# Document Sync — BasicAuth Outbound HTTP Mirror Probe (Design)

## Date

2026-04-07

## Goal

Add a minimal, scope-disciplined BasicAuth outbound HTTP probe to
`document_sync` so operators can validate that a configured `SyncSite` can
actually reach its remote mirror with the credentials currently stored on the
site row.

This is a **probe**, not a sync. It does not push or pull documents. It does
not mutate any state. It does not write any audit log. It is the minimum
viable connectivity / credential check.

## Non-Goals

- No pull / push of documents
- No retry / backoff / circuit breaker
- No alternative auth schemes (only `auth_type == "basic"`)
- No persistence of probe results
- No metrics / counters / drift recording
- No new database migration
- No change to the existing site/list/get masked-auth-config contract

## Surface

### Endpoint

`POST /api/v1/document-sync/sites/{site_id}/mirror-probe`

- Auth: requires logged-in user (`get_current_user`), no extra role gate
- No request body
- Returns probe outcome JSON

### Response shape (success)

```json
{
  "ok": true,
  "site_id": "site-1",
  "endpoint": "https://hq.example.com/api/v1/document-sync/overview",
  "status_code": 200,
  "remote_overview": { "...": "..." }
}
```

- `ok`: `True` iff `200 <= status_code < 300`
- `endpoint`: the URL the probe actually called
- `remote_overview`: parsed JSON body if remote returned JSON dict, else
  `null` (note: only attempted on 2xx)
- **The site password is never echoed** anywhere in the response

### Failure mapping (all → HTTP 400)

| Cause | ValueError detail (substring) |
|-------|-------------------------------|
| Site not found | `not found` |
| Site has no `base_url` | `no base_url` |
| Site `auth_type != "basic"` | `auth_type='basic'` |
| Basic auth contract missing username or password | `missing username or password` |
| Connection / timeout / DNS / etc. (`httpx.RequestError`) | `failed: <ExcClassName>` |
| Remote returned 401 | `rejected by remote (401)` |
| Remote returned 403 | `rejected by remote (403)` |
| Remote returned 2xx but body is not JSON | `non-JSON 2xx body` |

All other status codes (e.g., 5xx, 404) flow through as `ok=False` with the
status code reported. The router maps all `ValueError` to `HTTPException(400)`
following the existing document_sync router convention.

## Default probe URL

`{base_url.rstrip('/')}/api/v1/document-sync/overview`

Rationale:

- This endpoint already exists in the document_sync router and returns a JSON
  overview payload. It is the cheapest, side-effect-free endpoint exposed by
  a peer document_sync deployment.
- Using a hard-coded path keeps the probe contract minimal — no caller has to
  pick / pass a URL.

## Service-side implementation

Added to `DocumentSyncService` in `src/yuantus/meta_engine/document_sync/service.py`:

```python
def mirror_probe(self, site_id: str) -> Dict[str, Any]:
    site = self.get_site(site_id)
    if site is None:
        raise ValueError(f"Site '{site_id}' not found")

    base_url = (site.base_url or "").strip()
    if not base_url:
        raise ValueError(...)
    if site.auth_type != "basic":
        raise ValueError(...)

    auth_config = site.auth_config or {}
    username = str(auth_config.get("username") or "").strip()
    password = str(auth_config.get("password") or "").strip()
    if not username or not password:
        raise ValueError(...)

    endpoint = f"{base_url.rstrip('/')}{_MIRROR_PROBE_PATH}"

    try:
        with httpx.Client(timeout=_MIRROR_PROBE_TIMEOUT_S) as client:
            response = client.get(
                endpoint,
                auth=httpx.BasicAuth(username, password),
            )
    except httpx.RequestError as exc:
        raise ValueError(f"... failed: {type(exc).__name__}") from exc

    status_code = response.status_code
    if status_code in (401, 403):
        raise ValueError(...)

    remote_overview: Optional[Dict[str, Any]] = None
    if 200 <= status_code < 300:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("... non-JSON 2xx body") from exc
        if isinstance(payload, dict):
            remote_overview = payload

    return {"ok": ..., "site_id": site.id, "endpoint": endpoint,
            "status_code": status_code, "remote_overview": remote_overview}
```

Constants (module-level):

```python
_MIRROR_PROBE_PATH = "/api/v1/document-sync/overview"
_MIRROR_PROBE_TIMEOUT_S = 10.0
```

## Router-side implementation

`POST /document-sync/sites/{site_id}/mirror-probe` in
`src/yuantus/meta_engine/web/document_sync_router.py`:

```python
@document_sync_router.post("/sites/{site_id}/mirror-probe")
def mirror_probe_site(site_id, db, user):
    service = DocumentSyncService(db)
    try:
        return service.mirror_probe(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

This mirrors the existing `try/except ValueError → HTTPException(400)`
pattern used by `create_site`, `create_job`, and other write endpoints in the
same router.

## Why it is safe

- **No password leak**: the password is read from `site.auth_config` and
  passed only into `httpx.BasicAuth(...)`. It never appears in any log line,
  ValueError message, or response body. This is verified by an explicit test
  that asserts `"secret" not in str(result)`.
- **No state mutation**: no DB rows are written; no `session.flush()` or
  `session.commit()` is called from the probe path.
- **Bounded blast radius**: the probe is a single GET against a hard-coded
  path with a fixed 10s timeout. There is no retry loop.
- **Existing surface untouched**: the masked `auth_config` serializer used
  by `_site_dict` is not modified, so the existing site/list/get tests
  continue to pass.

## Test plan

See `DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md`.

## Files touched

- `src/yuantus/meta_engine/document_sync/service.py` — new constants, new method
- `src/yuantus/meta_engine/web/document_sync_router.py` — new endpoint
- `src/yuantus/meta_engine/tests/test_document_sync_service.py` — `TestMirrorProbe`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py` — 2 router tests
- `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md` (this doc)
- `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md`
- `docs/DELIVERY_DOC_INDEX.md`
