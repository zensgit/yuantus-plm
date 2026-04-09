# Document Sync Mirror Compatibility — Reading Guide

## Date

2026-04-07

## Who this is for

An engineer or reviewer encountering the Document Sync Mirror
Compatibility line for the first time. This is a **navigation** document —
it points at the per-package design + verification docs rather than
duplicating their content.

For the bottom-line "is it done?" answer, read the Final Summary first.

---

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary (design)** — closure statement, scope of the minimal
   line, sub-package roll-up, non-goals, guardrails.
2. **Final Summary (verification)** — per-package verification roll-up,
   cumulative test result, what this docs-only package changed.

### Full implementation path (10 docs, ~40 min)

1. Final Summary (design + verification)
2. Mirror compatibility adapter audit (design + verification)
3. Mirror site auth contract (design + verification)
4. BasicAuth HTTP mirror probe (design + verification)
5. BasicAuth HTTP mirror execute and job mapping (design + verification)

The follow-up coverage refresh (`non-dict 2xx`, `generic non-2xx`) is
folded into the execute package's verification doc; there is no separate
package doc for it.

---

## Document Map by Topic

### 1. Final Summary

*Answers: "Is the line complete? What is in / out of scope? What guardrails apply?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_FINAL_SUMMARY_20260407.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_FINAL_SUMMARY_20260407.md` |

### 2. Mirror Compatibility Adapter Audit

*Answers: "What did the existing surface look like before this line started? What gaps were identified?"*

| Doc | Path |
|-----|------|
| Audit Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_ADAPTER_AUDIT_20260406.md` |
| Audit Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_COMPATIBILITY_ADAPTER_AUDIT_20260406.md` |

### 3. Mirror Site Auth Contract

*Answers: "How is the BasicAuth credential pair stored, normalized, and masked on read? Why are username + password both required and non-empty?"*

| Doc | Path |
|-----|------|
| Auth Contract Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_MIRROR_SITE_AUTH_CONTRACT_20260407.md` |
| Auth Contract Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_MIRROR_SITE_AUTH_CONTRACT_20260407.md` |

Key code: `_normalize_site_auth` in `document_sync/service.py`,
`_site_dict` in `web/document_sync_router.py`. The masked serializer
turns `auth_config` into `{username, has_password: bool}` on every read
surface.

### 4. BasicAuth HTTP Mirror Probe

*Answers: "How does an operator validate that a configured site is reachable with its credentials, without writing any state?"*

| Doc | Path |
|-----|------|
| Probe Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md` |
| Probe Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_PROBE_20260407.md` |

Key surface: `POST /api/v1/document-sync/sites/{site_id}/mirror-probe` →
read-only GET against `{base_url}/api/v1/document-sync/overview`. All
failures map to `ValueError` → HTTP 400. Password never echoed.

### 5. BasicAuth HTTP Mirror Execute and Job Mapping

*Answers: "How does an operator turn a successful probe into a recorded local SyncJob? How is the remote payload mapped onto job aggregates? How are remote-side failures captured without raising 500?"*

| Doc | Path |
|-----|------|
| Execute Design | `docs/DESIGN_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md` |
| Execute Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOCUMENT_SYNC_BASIC_AUTH_HTTP_MIRROR_EXECUTE_AND_JOB_MAPPING_20260407.md` |

Key surface: `POST /api/v1/document-sync/sites/{site_id}/mirror-execute`
→ creates a `SyncJob` via the existing `create_job`, calls the remote
overview with `httpx.BasicAuth`, maps `total_jobs / total_conflicts /
total_errors` onto `total_documents / conflict_count / error_count`,
transitions to `completed` or `failed`. Pre-job ValueError → HTTP 400.
Post-job remote failures land as a persisted `failed` SyncJob with
`mirror_error` in `job.properties`. The same verification doc records the
follow-up `non-dict 2xx body` and `remote status <code>` failure-branch
tests.

### 6. Non-Goals / Guardrails

*Answers: "What is intentionally NOT in this line? What invariants must any future change respect?"*

Covered in the Final Summary (design) under §Non-goals and §Guardrails.
Quick recap:

**Non-goals** (intentionally out of scope, not gaps):

- Board / dashboard surface for mirror state
- Export of mirror outcomes
- Readiness or rollup aggregations across multiple mirrors
- Batch / fan-out execute
- Async / background runners
- Retry, backoff, circuit breakers
- Dedicated remote execute API on the peer side
- Additional auth schemes (OAuth, mTLS, header tokens, …)
- Per-document `SyncRecord` rows for mirror jobs

**Guardrails** (must hold for any future change on this line):

- Password is read only into `httpx.BasicAuth(...)` and never substituted
  into any logged or returned string.
- Remote-side errors never raise HTTP 500 from the mirror execute path —
  they always end up as a persisted `failed` SyncJob.
- Every outbound call is a single GET against a hard-coded path with a
  fixed 10 s timeout. No retry loop, no fan-out.
- Pre-job validation runs before `create_job`, so invalid configurations
  never produce orphan SyncJob rows.
- No new schema. Persistence reuses `SyncJob.properties`.

### 7. Current Minimal Supported Scope

*Answers: "What can I actually do with the mirror compatibility line today?"*

A `SyncSite` row that holds a `base_url` and a BasicAuth credential pair
can:

1. Be **created** via `POST /document-sync/sites` with a normalized,
   masked auth contract. The service layer also supports the same
   normalized update flow, but the current public router surface exposes
   create/list/get plus mirror probe/execute.
2. Be **listed and inspected** via `GET /document-sync/sites` and `GET
   /document-sync/sites/{id}` with the password masked to `has_password:
   bool`.
3. Be **probed** via `POST /document-sync/sites/{id}/mirror-probe` for
   connectivity and credential validity (read-only, no DB writes).
4. Be **executed** via `POST /document-sync/sites/{id}/mirror-execute`
   as a read-through against `{base_url}/api/v1/document-sync/overview`,
   producing a local `SyncJob` in `completed` or `failed` state with
   remote aggregates mapped onto job fields.

That is the entire current contract. Anything else is a deliberate
non-goal of this line.

---

## Key Source Files

| File | Role |
|------|------|
| `src/yuantus/meta_engine/document_sync/service.py` | `_normalize_site_auth`, `mirror_probe`, `mirror_execute`, plus existing site/job CRUD |
| `src/yuantus/meta_engine/web/document_sync_router.py` | `/sites`, `/sites/{id}`, `/sites/{id}/mirror-probe`, `/sites/{id}/mirror-execute`; masked `_site_dict` serializer |
| `src/yuantus/meta_engine/tests/test_document_sync_service.py` | `TestSiteCRUD`, `TestMirrorProbe`, `TestMirrorExecute` |
| `src/yuantus/meta_engine/tests/test_document_sync_router.py` | site / mirror-probe / mirror-execute router tests |

## Note on dates

All package files in this line are dated `20260406` (audit) or `20260407`
(everything else). The audit was the only sub-package landed on `0406`;
the contract / probe / execute / coverage / final-summary / reading-guide
work all landed on `0407`.
