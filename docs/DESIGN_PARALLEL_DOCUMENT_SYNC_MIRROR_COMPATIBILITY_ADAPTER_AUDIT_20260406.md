# Design: Document Sync Mirror Compatibility Adapter Audit

## Date

2026-04-06

## Scope

Audit current `document_sync` site/job/router surfaces to determine what is
still missing to support a BasicAuth-style mirror compatibility adapter.

## Current Capabilities (already implemented)

| Capability | Status | Evidence |
|-----------|:------:|---------|
| Site CRUD (`create/list/get/update/state`) | YES | `DocumentSyncService` site methods + `/document-sync/sites*` |
| Job CRUD (`create/list/get/state`) | YES | `DocumentSyncService` job methods + `/document-sync/jobs*` |
| Sync record tracking | YES | `add_record()` / `list_records()` / `job_summary()` |
| Direction model (`push/pull/bidirectional`) | YES | `SyncSite.direction` + `SyncJob.direction` |
| Site endpoint identity | YES | `SyncSite.base_url` + `site_code` |
| Rich analytics | YES | overview / reconciliation / replay / audit / drift / lineage / retention / freshness / watermarks |
| Export surfaces | YES | overview / conflicts / reconciliation / audit / drift / lineage / retention / watermarks |
| Router error mapping for local CRUD flows | YES | `ValueError -> HTTP 400/404` in `document_sync_router.py` |
| Job/result data model for mirror outcomes | YES | `SyncJob` + `SyncRecord` can store totals, conflicts, errors, checksums |

## Gap Matrix: Mirror Compatibility Target vs Current

| # | Concern | Current | Target parity | Gap? | Gap type | Suggested fix | Likely files |
|---|---------|---------|--------------|:----:|----------|--------------|-------------|
| G1 | Mirror auth contract | `SyncSite` has `base_url/site_code/properties`, but no typed auth profile | Explicit mirror auth contract for BasicAuth-compatible sites | YES | medium code | Add typed auth/profile fields or validated auth payload with masked serialization | `document_sync/models.py`, `document_sync/service.py`, `document_sync_router.py` |
| G2 | Secret handling / masking | No first-class credential model, no masked site serializer | Secrets accepted/stored safely and never echoed raw | YES | medium code | Add masked response shape and write-only credential input | `document_sync/service.py`, `document_sync_router.py` |
| G3 | Outbound mirror transport | No `httpx`/`requests`/adapter logic in `document_sync` module | Mirror adapter can call remote BasicAuth endpoint | YES | medium code | Add minimal outbound adapter layer for BasicAuth request execution | `document_sync/service.py` |
| G4 | Remote probe / execution contract | Current router only manages local sites/jobs/analytics | Probe or execute surface for mirror-compatible sync path | YES | medium code | Add focused adapter-facing service/router entrypoint | `document_sync_router.py`, `document_sync/service.py` |
| G5 | Remote response -> job/result mapping | `SyncJob` / `SyncRecord` can track results, but adapter does not populate them | Mirror execution result mapped into existing job + record model | YES | medium code | Reuse existing job/record schema and fill via adapter result mapper | `document_sync/service.py` |
| G6 | Analytics / export reuse | Already broad and export-ready | Mirror path should reuse existing analytics/exports instead of new board | NO | reusable | Reuse current summary/analytics/export surfaces | — |
| G7 | Full bidirectional sync policy | Generic direction model exists, but no transport-level policy | Product-grade mirror policy for push/pull/bidirectional execution | NO | future product | Not required for initial BasicAuth adapter parity | — |

## What Can Be Reused (no rework needed)

| Component | Why reusable |
|-----------|-------------|
| `SyncSite` identity fields | `base_url` + `site_code` already establish remote endpoint identity |
| `SyncJob` / `SyncRecord` schema | Existing totals, checksums, outcomes, conflict/error detail fit adapter results |
| `job_summary()` | Already produces downstream export-ready mirror result summary |
| Analytics/export layer | Existing overview / audit / drift / lineage / reconciliation surfaces should remain the reporting layer |
| Router CRUD/error pattern | Existing `ValueError -> HTTPException` style can be reused for adapter probe/execute errors |

## Classification

**MEDIUM CODE GAP** — not docs-only, not a tiny patch, not a large refactor.

The domain/reporting layer is complete, but the actual compatibility adapter
layer is missing. The missing pieces are bounded and local to the
`document_sync` module; no broader manufacturing or governance refactor is
needed.

## Minimum Implementation Plan

### Recommended: 2 packages

**Package 1: `document-sync-mirror-site-auth-contract`**
- Add explicit mirror auth/profile input contract
- Support BasicAuth-compatible site configuration
- Keep secrets write-only / masked in serialized responses
- Reuse existing `SyncSite` identity fields instead of rebuilding site CRUD
- Risk: Low-medium

**Package 2: `document-sync-basic-auth-http-mirror-adapter`**
- Add minimal outbound adapter using a BasicAuth-compatible HTTP client
- Add a focused probe/execute path
- Map remote execution result back into existing `SyncJob` / `SyncRecord`
- Reuse current analytics/export surfaces for observability
- Risk: Medium

### Recommended order

1. `document-sync-mirror-site-auth-contract`
2. `document-sync-basic-auth-http-mirror-adapter`

Package 1 should land first so the transport layer has a typed site contract to
consume. Package 2 then plugs into the already-mature job/result model.

## Why This Is Medium, Not Large

1. The site/job/result model already exists and is stable
2. Analytics/export surfaces already cover post-execution observability
3. The missing layer is the adapter contract + transport, not a new domain
4. The work is concentrated in `document_sync` service/router files
5. No new reporting/readiness surface is required for closure
