# CAD Dedup: SimilarityRecord -> Part Equivalent (S3 + Postgres + MinIO) (2026-02-12)

## Goal

Productize the 2D dedup workflow so it results in an actionable relationship:

- `cad_dedup_vision` produces SimilarityRecords (pending) from Dedup Vision search results
- a reviewer confirms a SimilarityRecord
- system creates a `Part Equivalent` relationship between the two Parts (if both drawings are attached to Parts)

Additionally:

- allow dedup batches to run with `index=true` (backfill/index historical drawings)
- ensure `dedup_index=true` can promote an existing pending dedup job that was created with `dedup_index=false` (dedupe-key reuse)

## Development Plan (Implemented)

1) SimilarityRecord unordered-pair uniqueness (DB-level)

- Add `SimilarityRecord.pair_key` and a unique constraint/index.
- Add an Alembic migration:
  - Add/backfill `pair_key` for existing records.
  - Delete historical duplicates (keep newest by `created_at`) so uniqueness can be enforced.
  - Create a unique index on `pair_key`.
- Update ingestion code to compute `pair_key` and use `INSERT .. ON CONFLICT DO NOTHING` for concurrency safety.

2) Dedup operational report + export

- Implement `DedupService.generate_report(...)` and `DedupService.list_records_for_export(...)`.
- Add endpoints:
  - `GET /api/v1/dedup/report`
  - `GET /api/v1/dedup/report/export` (CSV)

3) auto_trigger_workflow on confirm

- In `DedupService.review_record(...)`, after a record is confirmed and the relationship item exists:
  - If rule has `auto_trigger_workflow=true` and `workflow_map_id` configured, start the workflow for the relationship item.
  - Persist `workflow_map_id` and `workflow_process_id` on the relationship item properties for traceability.

4) Verification + CI hardening

- Extend `scripts/verify_cad_dedup_relationship_s3.sh` to cover:
  - auto-created `Part Equivalent` relationship
  - auto-trigger workflow task
  - batch run `index=true`
  - job promotion to `index=true`
  - SimilarityRecord `pair_key` uniqueness
  - report/export endpoints
- Add stdlib-only contract tests and wire them into the CI `contracts` job.

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
- SimilarityRecord unordered pair uniqueness:
  - Adds `pair_key` (unordered `source_file_id|target_file_id`) and enforces uniqueness at the DB level.
  - Enforces `pair_key` as `NOT NULL` (align with ORM + avoid NULL bypass).
  - Ingestion uses `ON CONFLICT DO NOTHING` to be concurrency-safe.
  - Files:
    - `src/yuantus/meta_engine/dedup/models.py`
    - `src/yuantus/meta_engine/dedup/service.py`
    - `migrations/versions/y1b2c3d4e7a3_add_similarity_record_pair_key.py`
    - `migrations/versions/y1b2c3d4e7a4_make_similarity_pair_key_not_null.py`
- Auto-trigger workflow on confirm:
  - When a SimilarityRecord is confirmed and the rule has `auto_trigger_workflow=true` + `workflow_map_id`, start a workflow for the created `Part Equivalent` relationship item.
  - Rule validation: `auto_trigger_workflow=true` requires `workflow_map_id` (HTTP 400 on create/update).
  - Files:
    - `src/yuantus/meta_engine/dedup/service.py`
- Dedup report + export:
  - Adds operational report endpoint and CSV export.
  - Files:
    - `src/yuantus/meta_engine/web/dedup_router.py`
    - `src/yuantus/meta_engine/dedup/service.py`
- Added end-to-end verification script:
  - `scripts/verify_cad_dedup_relationship_s3.sh`
- Dedup Vision search integration:
  - Prefer `/api/v2/search` (progressive engine) so newly indexed drawings are queryable immediately after `/api/index/add`.
  - Falls back to legacy `/api/search` for older deployments.
  - File: `src/yuantus/integrations/dedup_vision.py`
- Dedup Vision host-network fallback (docker worker hardening):
  - When `YUANTUS_DEDUP_VISION_BASE_URL` points to compose host `dedup-vision` but DNS is unavailable in the current worker network, client retries via `host.docker.internal:${DEDUP_VISION_PORT:-8100}`.
  - Supports explicit override `YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL` (and optional `YUANTUS_DEDUP_VISION_FALLBACK_PORT`).
  - Worker adds `extra_hosts: ["host.docker.internal:host-gateway"]` for Linux compatibility.
  - Files:
    - `src/yuantus/integrations/dedup_vision.py`
    - `docker-compose.yml`

## CI Contracts (Hardening)

To reduce regressions, the following stdlib-only contract tests are included in the CI `contracts` job:

- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_auto_trigger_workflow.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_batch_run_index.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_job_promotion.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_report_endpoints.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_similarity_pair_key.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_vision_host_fallback.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_dedup_vision_v2_fallback.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_compose_worker_dedup_vision_url.py` (ensures `docker-compose.yml` worker sets `YUANTUS_DEDUP_VISION_BASE_URL` so `cad_dedup_vision` jobs can reach Dedup Vision inside the container network)

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

Docker worker mode (more production-like; do not run local `yuantus worker --once`):

```bash
docker compose -f docker-compose.yml --profile dedup up -d worker
LOG=/tmp/verify_cad_dedup_relationship_s3_docker_worker_$(date +%Y%m%d-%H%M%S).log
USE_DOCKER_WORKER=1 scripts/verify_cad_dedup_relationship_s3.sh | tee "$LOG"
```

Expected:

- Outputs `ALL CHECKS PASSED`
- Confirms SimilarityRecord exists and becomes `confirmed`
- Confirms a `Part Equivalent` relationship exists via `GET /api/v1/items/{part_id}/equivalents`
- Confirms a workflow task is created for the `Part Equivalent` relationship (rule `auto_trigger_workflow=true`)
- Confirms batch run `index=true` results in `cad_dedup.indexed.success=true`
- Confirms dedupe promotion results in pending job payload containing `index=true`
- Confirms SimilarityRecord unordered pair uniqueness is enforced (`pair_key`)
- Confirms rule validation: `auto_trigger_workflow=true` requires `workflow_map_id` (HTTP 400)
- Confirms DB constraint: `pair_key` is `NOT NULL`
- Confirms dedup report + CSV export endpoints return rows

## Runbook: idonly + Dedup Vision (Docker Worker)

适用场景：

- API/Worker 运行在 `docker compose -p yuantusplm_idonly -f docker-compose.yml` 项目中
- `cad_dedup_vision` 任务由容器内 worker 执行（`USE_DOCKER_WORKER=1`）
- Dedup Vision 可能运行在另一个 compose 项目（例如默认 `yuantus`）并通过宿主 `8100` 暴露

启动顺序（推荐）：

```bash
# 1) 启动 Dedup Vision（如果尚未运行）
docker compose -f docker-compose.yml --profile dedup up -d dedup-vision

# 2) 启动 idonly 栈核心服务
docker compose -p yuantusplm_idonly -f docker-compose.yml up -d postgres minio api

# 3) 重建并启动 idonly worker（确保包含最新 host fallback + extra_hosts）
docker compose -p yuantusplm_idonly -f docker-compose.yml build worker
docker compose -p yuantusplm_idonly -f docker-compose.yml up -d --force-recreate worker
```

健康检查：

```bash
curl -sS -o /dev/null -w 'api=%{http_code}\n' http://127.0.0.1:7910/api/v1/health
curl -sS -o /dev/null -w 'dedup=%{http_code}\n' http://127.0.0.1:8100/health
docker inspect -f '{{json .HostConfig.ExtraHosts}}' yuantusplm_idonly-worker-1
docker exec yuantusplm_idonly-worker-1 python -c "import urllib.request;print(urllib.request.urlopen('http://host.docker.internal:8100/health', timeout=5).status)"
```

执行验证：

```bash
USE_DOCKER_WORKER=1 scripts/verify_cad_dedup_relationship_s3.sh
```

预期输出：

- `ALL CHECKS PASSED`

常见故障与处理：

- 症状：`result.ok=false` 且错误 `Name or service not known`（解析 `dedup-vision` 失败）
  - 处理：确认 worker 为最新镜像并已重建（`build worker` + `up --force-recreate worker`）。
  - 处理：确认 worker `extra_hosts` 包含 `host.docker.internal:host-gateway`。
  - 处理：确认宿主 `http://localhost:8100/health` 为 `200`。
- 症状：`http://127.0.0.1:7910` 不可达
  - 处理：检查端口冲突（可能被其它 compose 项目占用），并确保当前目标项目的 `api/postgres/minio` 在运行。

## Verification Results (2026-02-12)

### Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-IDONLY-DOCKER-WORKER-20260215-141144Z

- 时间：`2026-02-15 14:11:44 +0000`（本机时区：`2026-02-15 22:11:44 +0800`）
- 环境：`docker compose -p yuantusplm_idonly -f docker-compose.yml`（Postgres + MinIO + API + worker=compose container）；Dedup Vision 由宿主 `http://localhost:8100` 提供
- 命令：`USE_DOCKER_WORKER=1 scripts/verify_cad_dedup_relationship_s3.sh`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 备注：该场景此前会在 worker 内出现 `Name or service not known`（`dedup-vision` DNS 解析失败）；本次验证确认 host-network fallback 已生效。

关键 ID：

- workflow_map_id: `60b7ead9-c6ae-42e6-a340-b62822eaed36`
- rule_id: `c605b46d-68c2-4ae9-a1f0-2a11859ee8a3`
- part_a_id: `3e81f8de-355c-44f9-8fb0-fa285e3007b9`
- part_b_id: `a8dcf02c-2e0b-43ab-ad3f-5efcca959c26`
- baseline_file_id: `74bd1b54-2e98-46d7-845d-eed017481119`
- query_file_id: `914e6d6a-352d-4c33-b3fc-94d44552905f`
- baseline_job_id: `162a24b8-0d64-41a8-80ac-4628628d5eac`
- query_job_id: `45bb7372-f5bb-44ef-bc19-2205a6ece3e8`
- similarity_record_id: `9a71adcc-ab2e-46a8-84fe-a64caa7a352e`
- relationship_item_id: `ea21c282-08ae-476d-beba-dbf33622a49e`
- batch_id: `08ad5f68-0278-4ba2-93c6-c0c8e75b15c9`
- reverse_job_id: `53ed4974-b9c3-433b-b753-d35fbbb0266c`
- promote_file_id: `ce013184-8a69-4312-8f26-5d708c56b54b`
- promote_job_id: `3aa4952e-6e07-453d-a509-b5cc08181425`

### Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-DOCKER-WORKER-20260215-133023Z

- 时间：`2026-02-15 13:30:23 +0000`（本机时区：`2026-02-15 21:30:23 +0800`）
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision + worker=compose container；脚本使用 `USE_DOCKER_WORKER=1`）
- 命令：`USE_DOCKER_WORKER=1 scripts/verify_cad_dedup_relationship_s3.sh`
- 结果：`PASS`（`ALL CHECKS PASSED`）

关键 ID：

- workflow_map_id: `4875679c-6029-4517-adb2-c78d63a8f834`
- rule_id: `3b217b8f-8131-48f2-8a72-93e92ca84167`
- part_a_id: `b193fec6-0eff-457d-a85c-39ff7d9981ef`
- part_b_id: `a56f1cab-4a4c-495b-ba74-167d070e7bfd`
- baseline_file_id: `62dc412d-8e32-4242-8288-8311f1c4a294`
- query_file_id: `3764f8cf-de72-4f7f-b599-d38096d1a6ba`
- baseline_job_id: `3d1ac57f-fa84-430d-bde4-a842db64cd9e`
- query_job_id: `7cdb1ab4-5abe-49fb-9ac8-da8a917579d9`
- similarity_record_id: `c39541cb-38c6-431e-b3a5-178824c776cf`
- relationship_item_id: `75680db2-bd7a-4924-abcf-9767ac1ef8f7`
- batch_id: `d4f14cb9-54e6-46f5-bf19-6b0916ae3b3f`
- reverse_job_id: `90b3bee8-8230-4fe6-8ad9-5f6ca3103a55`
- promote_file_id: `a79959dd-8ed2-4592-82b0-98be0117e334`
- promote_job_id: `db5c230e-54ff-4126-abd2-9a4273151bb1`

### Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-20260214-174745Z

- 时间：`2026-02-14 17:47:45 +0000`（本机时区：`2026-02-15 01:47:45 +0800`）
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision；worker 由脚本内本地 CLI `yuantus worker --once` 轮询执行）
- 命令：`scripts/verify_cad_dedup_relationship_s3.sh`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 备注：
  - 启动时宿主机已有 `yuantusplm_idonly` 项目占用 `7910/55432/59000` 端口。
  - 本次验证期间临时停止冲突容器：`yuantusplm_idonly-api-1`、`yuantusplm_idonly-postgres-1`、`yuantusplm_idonly-minio-1`。
  - 验证完成后已使用 `docker compose -p yuantusplm_idonly -f docker-compose.yml up -d postgres minio api` 恢复。

关键 ID：

- workflow_map_id: `fadd1d64-ce74-4927-90a8-0691883f7cb0`
- rule_id: `7e51c548-6ce0-44dc-8114-6bb8842782a5`
- part_a_id: `9d9494f6-0fb3-45c9-9c93-117d6be119ab`
- part_b_id: `3ad78530-b3f2-422e-acf2-7515c9c3e1ed`
- baseline_file_id: `0ef41c28-abc8-4f21-a343-e3e51f04e917`
- query_file_id: `8bce154d-374a-4073-9a38-b3995af4f6eb`
- baseline_job_id: `2300c49c-b86e-4442-b683-0036f4d5a605`
- query_job_id: `8a625765-53cd-431f-94fb-cecefb0bb64c`
- similarity_record_id: `9568350d-f200-4215-a924-2c603a3771e4`
- relationship_item_id: `a5158ae0-c007-455b-88b9-b345a56d4f4a`
- batch_id: `1fa3f4ae-6de7-418b-a6b4-4a325f4ee4b5`
- reverse_job_id: `c6e63b08-7320-44d5-945a-938ee463780e`
- promote_file_id: `af361e3b-ac4c-4e83-97fe-608c32f312ba`
- promote_job_id: `08f99c03-45ff-4206-b4e5-e7c7f109d2b9`

### Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-DOCKER-WORKER-20260213-013516

- 时间：`2026-02-13 01:35:16 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision + worker=compose container；脚本使用 `USE_DOCKER_WORKER=1` 等待容器 worker 处理 job）
- 命令：`LOG=/tmp/verify_cad_dedup_relationship_s3_docker_worker_20260213-013516.log; USE_DOCKER_WORKER=1 scripts/verify_cad_dedup_relationship_s3.sh | tee "$LOG"`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 原始日志：`/tmp/verify_cad_dedup_relationship_s3_docker_worker_20260213-013516.log`

关键 ID：

- workflow_map_id: `9f226ef6-b970-41e4-84dc-1205b294c6e2`
- rule_id: `0d6c9ee1-2c5a-4c03-ba8d-1072d445ffe7`
- part_a_id: `b01c9688-51ad-4f3f-8d62-62086fe4f1f1`
- part_b_id: `652b2b56-204d-41bb-bfc9-2073c8737347`
- baseline_file_id: `792ef6cd-1b6e-4660-9dbd-c3e59ae1540d`
- query_file_id: `f47cf34e-fcaa-482d-b7d5-cebee3c153cf`
- baseline_job_id: `a6b39bd8-20b9-4da6-bc01-04e92290632b`
- query_job_id: `0ceae9b9-688f-43dc-a795-11197da9531e`
- similarity_record_id: `be6954cc-6730-40b2-b859-4eb614245221`
- relationship_item_id: `0463ea55-f0b2-4465-8a5a-cb105504a20b`
- batch_id: `d54ddf5a-61f1-4fe8-b44b-df66ec6aaafc`
- reverse_job_id: `e2aef774-6838-4cb2-a7bc-3a93c77f8181`
- promote_file_id: `07244275-1817-4b9d-bdb8-fc12c9ad3626`
- promote_job_id: `8ebc8860-5c56-4ae9-9647-271f039ea84c`

### Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-20260212-225211

- 时间：`2026-02-12 22:52:58 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision，worker 用本机 CLI 轮询执行）
- 命令：`LOG=/tmp/verify_cad_dedup_relationship_s3_20260212-225211.log; scripts/verify_cad_dedup_relationship_s3.sh | tee "$LOG"`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 原始日志：`/tmp/verify_cad_dedup_relationship_s3_20260212-225211.log`

关键 ID：

- workflow_map_id: `2dad5291-c67e-4c7b-8f0a-0e9540e27c02`
- rule_id: `7924dbaa-07f8-4766-9979-6a9b7274a8de`
- part_a_id: `ac70d991-5403-4f24-bfce-3a61779f9a29`
- part_b_id: `c3a738e4-af7c-4b6c-a1ab-39627842298c`
- baseline_file_id: `5bbc1e6e-2091-49a8-8bb8-59d7e9a6b7a9`
- query_file_id: `33f60fb0-b18c-47a8-896b-3861b1098cea`
- similarity_record_id: `e29b14a6-4c13-4de5-9fc3-dd822e134d6a`
- relationship_item_id: `ce5123e8-f027-45dd-b642-2652aac7c878`
- batch_id: `fac44a10-7e55-4595-8c90-fc215ef905f0`
- reverse_job_id: `574481fb-e549-410b-8d57-ac21e46b1200`
- promote_file_id: `46d2189b-41a6-4a70-ac26-6e9a5ca4a0c9`
- promote_job_id: `d3343d28-4d21-4f82-b590-f317fe52cc4b`

### Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-20260212-215323

- 时间：`2026-02-12 21:54:06 +0800`
- 环境：`docker compose -f docker-compose.yml --profile dedup`（Postgres + MinIO + API + Dedup Vision，worker 用本机 CLI 轮询执行）
- 命令：`LOG=/tmp/verify_cad_dedup_relationship_s3_20260212-215323.log; scripts/verify_cad_dedup_relationship_s3.sh | tee "$LOG"`
- 结果：`PASS`（`ALL CHECKS PASSED`）
- 原始日志：`/tmp/verify_cad_dedup_relationship_s3_20260212-215323.log`

关键 ID：

- workflow_map_id: `405a0868-d06e-4880-bc1d-62002b70db2e`
- rule_id: `778ddcaf-0fb1-4187-beb2-8f3d933b08ce`
- part_a_id: `70d910b4-3e6f-48ea-b73a-edb8fb41f41d`
- part_b_id: `37535e7b-0a7e-4266-ad70-b31013f38a70`
- baseline_file_id: `d41522da-2abc-48a6-86f3-0a568e10184a`
- query_file_id: `e505912e-4baa-4e59-aec5-bb60e1906f45`
- similarity_record_id: `33d72879-a991-4111-9bb9-a4cab2a162b5`
- relationship_item_id: `8a6ed2de-bb90-4934-931e-2b94c91c795a`
- batch_id: `ead459bd-9020-410f-afeb-deec6a9fe9f2`
- reverse_job_id: `1def885e-aa21-45a1-9b0c-1858122d8117`
- promote_file_id: `d6959bf2-2f73-4982-8ccd-c3ece1668f48`
- promote_job_id: `a895e292-fcda-4880-b546-5549d5b38a26`

### Run RUN-CAD-DEDUP-REL-S3-PG-MINIO-20260212-195201

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
