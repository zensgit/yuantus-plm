# C39 — Document Sync Freshness / Watermarks Bootstrap — Design

## Overview

Extends the document_sync domain with freshness scoring, watermark thresholds,
and export helpers for fleet-wide document sync health monitoring.

## Service Methods

| Method | Purpose |
|---|---|
| `freshness_overview()` | Fleet-wide freshness summary: total sites, stale count, avg freshness %, freshest/stalest sites |
| `watermarks_summary()` | Watermark thresholds per site: high/low watermarks, exceeded count |
| `site_freshness(site_id)` | Per-site freshness detail: synced vs stale counts, freshness % |
| `export_watermarks()` | Combined export payload: freshness overview + watermarks + per-site details |

## Router Endpoints

| Method | Path | Handler |
|---|---|---|
| GET | `/freshness/overview` | `freshness_overview` |
| GET | `/watermarks/summary` | `watermarks_summary` |
| GET | `/sites/{site_id}/freshness` | `site_freshness` (404 on missing site) |
| GET | `/export/watermarks` | `export_watermarks` |

## Freshness Model

- **Fresh**: Documents with `synced` outcome
- **Stale**: Documents with `conflict`, `error`, or `skipped` outcome
- **Freshness %**: `synced / total_records * 100`
- **Watermark threshold**: 50% — sites below this are flagged as exceeded

## Data Flow

```
SyncSite -> SyncJob (per-site) -> aggregate synced/conflict/error/skipped
    -> compute freshness_pct per site
    -> derive watermarks (high = freshness%, low = 100 - freshness%)
    -> flag exceeded if freshness% < threshold
```
