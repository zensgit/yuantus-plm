# C18 – Document Multi-Site Sync Bootstrap – Design

## Goal
- 在独立 `document_sync` 子域内建立 multi-site sync bootstrap。
- Remote site management, sync job lifecycle, per-document record tracking,
  and conflict/checksum summary export.

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Deliverables
- remote site model (SyncSite)
- sync job model (SyncJob)
- per-document sync record model (SyncRecord)
- checksum/conflict summary read model
- 7 API endpoints (site + job CRUD, job summary)

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 storage / CAD 热路径
- No background workers in this increment

## Data Model

### Enums
- `SiteState`: active, disabled, archived
- `SyncJobState`: pending, running, completed, failed, cancelled
- `SyncDirection`: push, pull, bidirectional
- `SyncRecordOutcome`: synced, skipped, conflict, error

### SyncSite (`meta_sync_sites`)
| Column | Type | Notes |
|--------|------|-------|
| id | String PK | UUID |
| name | String(200) | required |
| description | Text | optional |
| base_url | String(500) | remote endpoint |
| site_code | String(60) | unique identifier |
| state | String(30) | default "active" |
| direction | String(30) | default "push" |
| is_primary | Boolean | default False |
| properties | JSON/JSONB | extensible |
| created_at, created_by_id, updated_at | audit | |

### SyncJob (`meta_sync_jobs`)
| Column | Type | Notes |
|--------|------|-------|
| id | String PK | UUID |
| site_id | FK → meta_sync_sites.id | indexed |
| state | String(30) | default "pending" |
| direction | String(30) | default "push" |
| document_filter | JSON/JSONB | scope filter |
| total_documents, synced_count, conflict_count, error_count, skipped_count | Integer | counters |
| started_at, completed_at | DateTime | timing |
| duration_seconds | Float | computed |
| error_message | Text | failure detail |
| properties | JSON/JSONB | extensible |
| created_at, created_by_id | audit | |

### SyncRecord (`meta_sync_records`)
| Column | Type | Notes |
|--------|------|-------|
| id | String PK | UUID |
| job_id | FK → meta_sync_jobs.id | indexed |
| document_id | String | indexed |
| source_checksum, target_checksum | String(128) | checksums |
| outcome | String(30) | default "synced" |
| conflict_detail, error_detail | Text | details |
| created_at | DateTime | audit |

## State Machines

### Site: `active ⇄ disabled → archived (terminal)`
### Job: `pending → running → completed|failed|cancelled (terminal)`

## API Endpoints

`document_sync_router = APIRouter(prefix="/document-sync", tags=["Document Sync"])`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sites` | Create site |
| GET | `/sites` | List (filters: state, direction) |
| GET | `/sites/{site_id}` | Get single |
| POST | `/jobs` | Create job (validates site active) |
| GET | `/jobs` | List (filters: site_id, state) |
| GET | `/jobs/{job_id}` | Get single |
| GET | `/jobs/{job_id}/summary` | Conflict/checksum summary |

## Codex Integration Notes
- `C18` was integrated on top of the frozen unified stack branch in:
  - `feature/codex-c18-document-sync-integration`
- The greenfield isolation contract was preserved:
  - no app registration
  - no edits to storage / CAD hot paths
- Extensible JSON fields remain portable across the current test/storage baseline by using:
  - `JSON().with_variant(JSONB, "postgresql")`
