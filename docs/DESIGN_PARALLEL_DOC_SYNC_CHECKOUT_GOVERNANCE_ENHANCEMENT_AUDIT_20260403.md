# Design: Doc-Sync Checkout Governance Enhancement Audit

## Date

2026-04-03

## Scope

Audit current doc-sync + checkout gate implementation to determine what's
needed to reach B2 (checkout strictness) + B1 (direction dimensions) parity.

## Current Capabilities (already implemented)

| Capability | Status | Evidence |
|-----------|:------:|---------|
| Per-site direction model (push/pull/bidirectional) | YES | SyncSite.direction column + list_sites(direction=) |
| Per-item/version/document gate evaluation | YES | evaluate_checkout_sync_gate() in parallel_tasks_service |
| Pending/processing/failed/dead-letter counting | YES | 4-status counting in gate (lines 808-847) |
| Dead-letter detection (max-retry exhausted) | YES | _is_dead_letter_job() helper (lines 526-538) |
| Dead-letter-only blocking mode | YES | block_on_dead_letter_only parameter |
| Configurable thresholds (max_pending/processing/failed/dead_letter) | YES | Gate parameters (lines 783-794) |
| Blocking response with reasons + sample jobs | YES | Gate response (lines 869-885) |
| Rich analytics (40+ service methods) | YES | overview, analytics, conflicts, reconciliation, freshness, watermarks, audit, drift, lineage, checkpoints |
| Export surfaces (overview, conflicts, reconciliation, audit, drift, lineage, retention, watermarks) | YES | 8 export endpoints in doc_sync_router |
| Dead-letter listing + batch replay | YES | parallel_tasks_router (lines 404-466) |
| Checkout integration (HTTP 409 on block) | YES | version_router checkout handler (lines 178-192) |

## Gap Matrix: B2 + B1 Target vs Current

| # | Concern | Current | Target parity | Gap? | Gap type | Suggested fix | Files |
|---|---------|---------|--------------|:----:|----------|--------------|-------|
| G1 | Direction-aware gate | Gate counts all jobs regardless of direction | Gate should filter by site direction | YES | medium code | Add `direction` filter to job query in gate eval | parallel_tasks_service.py |
| G2 | Warn vs block mode | Only block (HTTP 409) or dead-letter-only | Separate warn (advisory) + block (enforce) responses | YES | medium code | Add `mode` param + split response into warn_reasons/block_reasons | parallel_tasks_service.py, version_router.py |
| G3 | Asymmetric direction thresholds | Single threshold set for all jobs | Push and pull have independent thresholds | YES | medium code | Add direction_thresholds dict param | parallel_tasks_service.py |
| G4 | Per-direction response | Single boolean `blocking` | Per-direction verdict in response | YES | medium code | Restructure gate response | parallel_tasks_service.py |
| G5 | Push/pull conflict strategy | Generic conflict detection | Direction-specific reconciliation policy | NO | future product | Not needed for B2 gate | — |
| G6 | Directional freshness enforcement | Global tracking only | Per-direction freshness in gate | NO | future product | Not needed for B2 gate | — |
| G7 | Directional watermark enforcement | Global tracking only | Per-direction watermark in gate | NO | future product | Not needed for B2 gate | — |

## What Can Be Reused (no rework needed)

| Component | Why reusable |
|-----------|-------------|
| `evaluate_checkout_sync_gate()` structure | Extend with direction + mode params; don't rebuild |
| Job status counting logic (lines 808-847) | Add direction filter to existing query, don't restructure |
| Gate response shape (lines 869-885) | Extend with direction_verdict + warn_reasons; don't break existing keys |
| Checkout handler in version_router | Add warn-mode passthrough; keep existing 409 logic |
| Doc-sync analytics surfaces | Already direction-aware in models; no changes needed |
| Dead-letter detection | Works for both directions; no changes needed |

## Classification

**MEDIUM CODE GAP** — not tiny, not a large refactor.

G1-G4 are real code changes but scoped to ~80-100 LOC total across 2 files.
G5-G7 are future product decisions, not needed for B2 closure.

## Minimum Implementation Plan

### Recommended: 2 packages

**Package 1: `doc-sync-gate-direction-filter` (B1 direction dimension)**
- Add `direction: Optional[str] = None` to `evaluate_checkout_sync_gate()`
- Filter job query by direction when provided
- Add direction to gate response
- ~30 LOC in parallel_tasks_service.py
- ~5 LOC in version_router.py (pass direction param)
- Risk: Low

**Package 2: `doc-sync-gate-warn-block-mode` (B2 checkout strictness)**
- Add `mode: str = "block"` param (warn/block)
- Split response into `warn_reasons` + `block_reasons`
- Checkout handler: warn mode returns 200 with advisory, block mode returns 409
- Support asymmetric thresholds via direction_thresholds dict
- ~50 LOC in parallel_tasks_service.py
- ~15 LOC in version_router.py
- Risk: Low-medium (changes gate response shape, but additive)

### Recommended order: Package 1 first, then Package 2

Package 1 is simpler and independently valuable. Package 2 builds on
direction-awareness.

## Why This Is Medium, Not Large

1. The gate evaluation method already exists and works
2. Direction is already stored in models — just needs query filter
3. Response shape is additive (new keys, existing keys preserved)
4. No new service classes or router files needed
5. No model migrations needed
6. ~80-100 LOC total across 2 packages
