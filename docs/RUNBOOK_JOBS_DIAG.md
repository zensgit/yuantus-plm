# Jobs 诊断 Runbook

目的：快速定位 CAD/异步任务失败的根因（文件缺失、权限、转换器、外部服务）。

## 0) 前置条件

- 已完成登录并获得 `$TOKEN`
- 已知 `job_id` 或 `file_id`
- 若使用 Postgres：可访问数据库（psql）

## 1) 查 job（API）

```bash
# 按 job_id 查询
curl -s http://127.0.0.1:7910/api/v1/jobs/<job_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'

# 按 file_id 过滤（更快定位）
curl -s 'http://127.0.0.1:7910/api/v1/jobs?file_id=<file_id>&limit=20' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

### 关注字段

- `status` / `last_error`
- `payload.error` / `payload.error_history`
- `diagnostics`（包含 storage path、cad_format、preview/geometry 路径、storage_exists）

## 2) 查文件元数据（API）

```bash
curl -s http://127.0.0.1:7910/api/v1/file/<file_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

关注：

- `system_path`（存储路径）
- `preview_path` / `geometry_path`
- `conversion_status` / `conversion_error`

## 3) 查 CAD 变更日志（Postgres）

```bash
psql postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1 \
  -c "SELECT action, payload, created_at FROM cad_change_logs WHERE file_id='<file_id>' ORDER BY created_at DESC LIMIT 5;"
```

关注：

- `action = job_failed`
- `payload.error_code` / `payload.error_message`

## 4) 常见错误与定位

- `source_missing`  
  - 说明：存储对象不存在（S3 key 或本地路径缺失）
  - 处理：核查 `system_path` 与 `storage_exists`

- `connector_failed`  
  - 说明：CAD connector 调用失败
  - 处理：检查 connector 服务健康、token、超时、格式支持

- `file_not_found` / `missing_file_id`  
  - 说明：DB 数据或 job payload 不完整
  - 处理：核查 `file_id` 是否存在、job payload 是否被裁剪

更多错误码说明：见 `docs/ERROR_CODES_JOBS.md`。

## 5) 快速复现（推荐）

```bash
# 生成并跑一条 CAD pipeline
TENANCY_MODE_ENV=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  scripts/verify_cad_pipeline_s3.sh
```
