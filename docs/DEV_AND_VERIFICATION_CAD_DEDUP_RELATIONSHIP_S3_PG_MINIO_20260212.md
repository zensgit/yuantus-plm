# CAD Dedup: SimilarityRecord -> Part Equivalent (S3 + Postgres + MinIO) (2026-02-12)

## Goal

Productize the 2D dedup workflow so it results in an actionable relationship:

- `cad_dedup_vision` produces SimilarityRecords (pending) from Dedup Vision search results
- a reviewer confirms a SimilarityRecord
- system creates a `Part Equivalent` relationship between the two Parts (if both drawings are attached to Parts)

Additionally:

- allow dedup batches to run with `index=true` (backfill/index historical drawings)
- ensure `dedup_index=true` can promote an existing pending dedup job that was created with `dedup_index=false` (dedupe-key reuse)

## Changes

- 2D classification:
  - PNG/JPG/JPEG imports are classified as `document_type=2d` (not `other`) so Dedup rules for `document_type=2d` apply.
  - File: `src/yuantus/meta_engine/web/cad_router.py`
- Dedup batch indexing:
  - `POST /api/v1/dedup/batches/{id}/run` request supports `index: bool`
  - Jobs created by a batch include `"index": true|false` in payload.
  - Files:
    - `src/yuantus/meta_engine/web/dedup_router.py`
    - `src/yuantus/meta_engine/dedup/service.py`
- Dedup job promotion (dedupe-key reuse):
  - If a `cad_dedup_vision` job is deduped to an existing pending/processing job but the new request has `index=true`, the existing job payload is promoted to `index=true` (best-effort).
  - Worker refreshes job payload before execution so late promotions can still be picked up.
  - Files:
    - `src/yuantus/meta_engine/services/job_service.py`
    - `src/yuantus/meta_engine/services/job_worker.py`
- Added end-to-end verification script:
  - `scripts/verify_cad_dedup_relationship_s3.sh`
- Dedup Vision search integration:
  - Prefer `/api/v2/search` (progressive engine) so newly indexed drawings are queryable immediately after `/api/index/add`.
  - Falls back to legacy `/api/search` for older deployments.
  - File: `src/yuantus/integrations/dedup_vision.py`

## CI Contracts (Hardening)

To reduce regressions, the following stdlib-only contract tests are included in the CI `contracts` job:

- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_batch_run_index.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_job_promotion.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_vision_v2_fallback.py`

## Verification

Bring up dependencies (Dedup profile):

```bash
docker compose -f docker-compose.yml --profile dedup up -d postgres minio api dedup-vision
docker compose -f docker-compose.yml --profile dedup up -d --build --no-deps api
```

Run:

```bash
LOG=/tmp/verify_cad_dedup_relationship_s3_$(date +%Y%m%d-%H%M%S).log
scripts/verify_cad_dedup_relationship_s3.sh | tee "$LOG"
```

Expected:

- Outputs `ALL CHECKS PASSED`
- Confirms SimilarityRecord exists and becomes `confirmed`
- Confirms a `Part Equivalent` relationship exists via `GET /api/v1/items/{part_id}/equivalents`
- Confirms batch run `index=true` results in `cad_dedup.indexed.success=true`
- Confirms dedupe promotion results in pending job payload containing `index=true`

## Verification Results (2026-02-12)

- 时间：`2026-02-12 19:52:01 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision，worker 用本机 CLI 轮询执行）
- 命令：`scripts/verify_cad_dedup_relationship_s3.sh`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 原始日志：`/tmp/verify_cad_dedup_relationship_s3_20260212-195201.log`

关键 ID：

- rule_id: `417b5d29-3ad4-4f62-8f86-7253b7768cb8`
- part_a_id: `57e7a8ff-1ec3-4009-a8e5-655a5fc8def1`
- part_b_id: `4cec8f44-0dcc-4036-b0c8-9a1b9a96692d`
- baseline_file_id: `704cdd14-3470-4bb9-ac30-ada062575150`
- query_file_id: `6172b349-dd8f-4ea4-9cca-b54f33fb5f49`
- similarity_record_id: `b28358a7-a2d1-4195-b50c-b47eaf8041ba`
- relationship_item_id: `22770b0e-ed42-4339-ab0f-7e6a4b2902f0`
- batch_id: `d85487ee-a051-4214-8cb6-41db775e7b86`
- promote_file_id: `6b0a7e76-e010-409c-97bb-42dce9e667ad`
- promote_job_id: `7958abc5-11dd-473b-b645-7cd64721abee`
