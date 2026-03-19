# C18 Document Multi-Site Sync Bootstrap Design

## Goal
- 在独立 `document_sync` 子域内建立 multi-site sync bootstrap。

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Deliverables
- remote site model
- sync job bootstrap read model
- checksum/conflict summary API

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 storage / CAD 热路径
