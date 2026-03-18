# C7 – BOM Compare and Summarized Snapshot Hardening

**Branch**: `feature/claude-c7-bom-compare`
**Date**: 2026-03-18
**Status**: Implemented & Verified

---

## 1. Objective

Extend the existing BOM compare pipeline with:
- A summarized row-based read model that flattens add/remove/change into
  quantity-delta rows
- Snapshot persistence (in-memory) allowing users to save, list, and retrieve
  named snapshots of summarized comparisons
- Snapshot-vs-snapshot and snapshot-vs-current diff endpoints
- CSV/Markdown/JSON export for all views

## 2. New Endpoints (8)

### 2.1 Summarized Compare

| Method | Path | Description |
|---|---|---|
| GET | `/bom/compare/summarized` | Compare two BOM trees with forced `summarized` mode, returns flat rows |
| GET | `/bom/compare/summarized/export` | Export summarized rows as csv/md/json |

### 2.2 Snapshot CRUD

| Method | Path | Description |
|---|---|---|
| POST | `/bom/compare/summarized/snapshots` | Create a named snapshot from live compare |
| GET | `/bom/compare/summarized/snapshots` | List snapshots with paging + filters |
| GET | `/bom/compare/summarized/snapshots/{id}` | Get snapshot detail with rows |
| GET | `/bom/compare/summarized/snapshots/{id}/export` | Export single snapshot as csv/md/json |

### 2.3 Snapshot Diff

| Method | Path | Description |
|---|---|---|
| GET | `/bom/compare/summarized/snapshots/compare` | Diff two saved snapshots row-by-row |
| GET | `/bom/compare/summarized/snapshots/compare/export` | Export snapshot diff |
| GET | `/bom/compare/summarized/snapshots/{id}/compare/current` | Diff snapshot vs current live state |
| GET | `/bom/compare/summarized/snapshots/{id}/compare/current/export` | Export snapshot-vs-current diff |

## 3. Row Model

Each summarized row contains:

```
line_key, parent_id, child_id, status (added|removed|changed),
quantity_before, quantity_after, quantity_delta,
uom_before, uom_after,
relationship_id_before, relationship_id_after,
severity, change_fields[]
```

Summary includes: `total`, `total_rows`, `added`, `removed`, `changed`,
`changed_major`, `quantity_delta_total`.

## 4. Snapshot Storage

In-memory thread-safe list with `threading.Lock`. Each snapshot stores:
- `snapshot_id` (prefixed `bom-compare-summarized-snapshot-{uuid}`)
- `created_at`, `created_by`, `name`, `note`
- `compare` (original query parameters for reproducibility)
- `summary`, `rows`, `row_total`

## 5. Diff Algorithm

Row-by-row key matching on `line_key`:
- Present in left only → `removed`
- Present in right only → `added`
- Present in both → compare 9 fields; if any differ → `changed` with `changed_fields` list

## 6. Design Decisions

1. **Reuses `compare_bom` endpoint function directly** – no service layer
   duplication; all new endpoints call the existing compare pipeline with
   `compare_mode="summarized"` forced.

2. **In-memory store** – appropriate for snapshot lifecycle; persisting to DB
   can be added later without API contract changes.

3. **Export format validation** – `json`, `csv`, `md` accepted; other formats
   return 400 with clear error message.

4. **Route ordering** – `/compare/summarized/snapshots/compare` registered
   before `/compare/summarized/snapshots/{snapshot_id}` to avoid path
   parameter capture conflicts.
