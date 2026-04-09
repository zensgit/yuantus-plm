# Document Sync Mirror Compatibility — Final Summary (Design)

## Date

2026-04-07

## Closure Statement

The minimal Document Sync Mirror Compatibility line is **complete**. The
following five sub-packages have all landed and been verified:

1. **Mirror compatibility audit: COMPLETE**
2. **Site auth contract: COMPLETE**
3. **BasicAuth probe: COMPLETE**
4. **Execute + job mapping: COMPLETE**
5. **Coverage follow-up (non-dict 2xx, generic non-2xx): COMPLETE**
6. **No known blocking gaps for the minimal mirror compatibility line.**

This document is the design-side closure marker. The sibling
`DEV_AND_VERIFICATION_..._FINAL_SUMMARY_20260407.md` records test results.

## Scope of "minimal mirror compatibility line"

A `SyncSite` row that holds a `base_url` and a BasicAuth credential pair
can:

1. Be **created and updated** with a normalized, masked auth contract.
2. Be **probed** for connectivity and credential validity (read-only,
   side-effect-free).
3. Be **executed** as a read-through against the remote `overview`
   endpoint, persisting the outcome as a local `SyncJob` in `completed` or
   `failed` state, with the remote payload mapped onto job aggregates.

That is the entire minimal contract. Anything beyond — board, export,
readiness rollups, batch fan-out, retry/backoff, dedicated remote execute
APIs, async/background runners — is explicitly **out of scope** for this
line and tracked separately if/when needed.

## Sub-package roll-up

### 1. Mirror compatibility adapter audit

| Doc | Path |
|-----|------|
| Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_ADAPTER_AUDIT_20260406.md` |
| Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_ADAPTER_AUDIT_20260406.md` |

Purpose: characterize the existing document_sync surface and identify the
minimum gaps that needed to be closed before a real outbound mirror call
could be made. Output: a 4-step closure roadmap (auth contract → probe →
execute → coverage follow-up).

### 2. Mirror site auth contract

| Doc | Path |
|-----|------|
| Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_SITE_AUTH_CONTRACT_20260407.md` |
| Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_SITE_AUTH_CONTRACT_20260407.md` |

Output: `_normalize_site_auth` private helper, `auth_type ∈ {"none",
"basic"}`, `auth_config = {username, password}` (both required, both
non-empty), masked-on-read serializer (`auth_config` becomes
`{username, has_password: bool}` in `_site_dict`). Update path also
normalizes through the same helper.

### 3. BasicAuth HTTP mirror probe

| Doc | Path |
|-----|------|
| Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md` |
| Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md` |

Output: `DocumentSyncService.mirror_probe(site_id)` and `POST
/document-sync/sites/{site_id}/mirror-probe`. Read-only side-effect-free
GET against `{base_url}/api/v1/document-sync/overview` with `httpx.BasicAuth`
and a 10s timeout. All failure causes (missing site, no `base_url`, no
basic auth contract, `httpx.RequestError`, 401, 403, non-JSON 2xx) map to
`ValueError` → HTTP 400. Password never echoed.

### 4. BasicAuth HTTP mirror execute and job mapping

| Doc | Path |
|-----|------|
| Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md` |
| Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md` |

Output: `DocumentSyncService.mirror_execute(site_id)` and `POST
/document-sync/sites/{site_id}/mirror-execute`. Reuses `create_job` /
`transition_job_state`. Maps `remote.total_jobs / total_conflicts /
total_errors` onto `job.total_documents / conflict_count / error_count`,
derives `synced_count`, stores remote payload + endpoint + status_code in
`job.properties`. Pre-job ValueError → HTTP 400; post-job remote-side
failure → persisted `failed` SyncJob with `mirror_error` in
`job.properties`. Same coverage doc covers the follow-up that added
`non-dict 2xx body` and `remote status <code>` failure-branch tests.

## Linkage map

```
[ Site row ] ── _normalize_site_auth ──> [ basic auth contract ]
      │                                            │
      ▼                                            ▼
[ POST /sites/{id}/mirror-probe ]    [ POST /sites/{id}/mirror-execute ]
      │                                            │
      ▼                                            ▼
read-only outbound GET            read-through GET → SyncJob
(probe result, no DB write)       (completed | failed) + job aggregates
```

The probe and execute endpoints share:

- The same hard-coded remote path (`_MIRROR_PROBE_PATH = "/api/v1/
  document-sync/overview"`).
- The same 10s timeout (`_MIRROR_PROBE_TIMEOUT_S = 10.0`).
- The same `httpx.BasicAuth` construction (no other auth scheme is
  supported).
- The same password-non-leak guarantee (verified by explicit assertions).

## Non-goals (intentional)

These are deliberately **not** part of the minimal mirror compatibility
line. If they are ever needed they belong to follow-up packages with their
own audit / design / verification cycle:

- Board / dashboard surface for mirror state
- Export of mirror outcomes
- Readiness or rollup aggregations across multiple mirrors
- Batch / fan-out execute across many sites in one call
- Async / background runners
- Retry, backoff, circuit breakers
- Dedicated remote execute API on the peer side (currently we read-through
  the existing `overview` endpoint)
- Additional auth schemes (OAuth, mTLS, header tokens, etc.)
- Per-document `SyncRecord` rows for mirror jobs (the remote `overview`
  payload does not expose per-document detail; we deliberately do not
  fabricate records)

## Guardrails

- **Password never echoed**: read from `site.auth_config`, used only in
  `httpx.BasicAuth(...)`, never substituted into any error string, log
  line, job property, or response field. Verified at every layer by
  explicit `"secret" not in str(result)` assertions.
- **Failure containment**: a remote-side error never raises HTTP 500. The
  router only ever sees a clean dict or a pre-job `ValueError` (which it
  maps to 400).
- **Bounded blast radius**: every outbound call is a single GET against a
  hard-coded path with a 10s fixed timeout. No retry loop. No fan-out.
- **Pre-job validation does not write rows**: missing site / base_url /
  auth contract raise before `create_job` is called, so invalid
  configurations never produce orphan SyncJob rows.
- **No new schema**: persistence reuses the existing `SyncJob` row, with
  failure detail living inside the existing `properties` JSON column.

## Files touched across the line (cumulative)

- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_service.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_ADAPTER_AUDIT_20260406.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_ADAPTER_AUDIT_20260406.md`
- `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_SITE_AUTH_CONTRACT_20260407.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_SITE_AUTH_CONTRACT_20260407.md`
- `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md`
- `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md`
- `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md`
- `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_FINAL_SUMMARY_20260407.md` (this doc)
- `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_FINAL_SUMMARY_20260407.md`
- `docs/DOCUMENT_SYNC_MIRROR_COMPATIBILITY_READING_GUIDE_20260407.md`
- `docs/DELIVERY_DOC_INDEX.md`

No new database migration was introduced anywhere on this line.
