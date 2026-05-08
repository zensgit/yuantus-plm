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

## 6) DedupCAD Vision 断路器（Phase 6 P6.1）

Phase 6 P6.1 为 DedupCAD Vision 客户端加装了断路器，**默认关闭**，开启后
连续失败超过阈值即短路后续调用，阻止重试风暴拖垮上游恢复窗口。后续
P6.2 / P6.3 会以同样模式接 `cad-ml` / `Athena`。

### 启用

通过环境变量切换（默认 false 即 status-quo）：

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `YUANTUS_CIRCUIT_BREAKER_DEDUP_VISION_ENABLED` | `false` | 总开关；上线前先在测试环境置 `true` 验收 |
| `YUANTUS_CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD` | `5` | 滚动窗口内连续失败次数到此即开路 |
| `YUANTUS_CIRCUIT_BREAKER_DEDUP_VISION_WINDOW_SECONDS` | `60` | 失败计数滚动窗口（秒） |
| `YUANTUS_CIRCUIT_BREAKER_DEDUP_VISION_RECOVERY_SECONDS` | `30` | 开路后多少秒进入半开试探 |
| `YUANTUS_CIRCUIT_BREAKER_DEDUP_VISION_HALF_OPEN_MAX_CALLS` | `1` | 半开期允许同时发出的试探调用数 |
| `YUANTUS_CIRCUIT_BREAKER_DEDUP_VISION_BACKOFF_MAX_SECONDS` | `600` | 重复触发开路时指数退避的上限 |

### 状态查询

API（json，免 Prometheus 即可看）：

```bash
curl -s http://127.0.0.1:7910/api/v1/health/deps \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.external.dedup_vision.breaker'
```

返回字段含义：

- `state`：`closed` / `open` / `half_open`
- `failures_in_window`：当前窗口内连续失败计数
- `current_recovery_seconds`：当前实际生效的开路恢复秒数（含指数退避）
- `opens_total` / `short_circuited_total` / `failures_total` / `successes_total`：
  累计计数器（与 Prometheus 同源）

Prometheus（建议告警）：

```promql
# 当前开路即告警
yuantus_circuit_breaker_state{name="dedup_vision",state="open"} == 1

# 短路次数突增
rate(yuantus_circuit_breaker_short_circuited_total{name="dedup_vision"}[5m]) > 1
```

### 故障处理流程

1. 看 `state`：若 `open`，记录 `current_recovery_seconds` 与
   `consecutive_open_cycles`。
2. 直接 curl 上游 `dedupcad-vision` `/health` 排查（绕过断路器，确认是
   服务真崩还是网络抖动）。
3. 上游恢复后无需手动重置：半开试探调用成功即自动 closed。
4. 紧急关断点：把 `YUANTUS_CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=false`
   重启服务即可还原老链路（透传 + 重试），代价是失去断路保护。

### 误开判处理

若怀疑断路器**误开**（上游正常但短路了）：

1. 检查 `failure_threshold` 是否过低；调整环境变量后重启进程生效。
2. 检查 `window_seconds` 是否过宽（包含历史故障）。
3. 短期豁免直接关旗标即可，配合 `successes_total` 在 5 分钟内涨为
   通过判据。

## 7) CAD ML Platform 断路器（Phase 6 P6.2）

P6.2 在 P6.1 基础上为 CAD ML Platform 客户端加装相同形态的断路器，
**默认关闭**。失败分类策略、metrics、`/health/deps` JSON 块、
故障处理流程与 §6 完全一致，区别仅在配置前缀（`CAD_ML`）与
breaker name（`cad_ml`）。

### 启用

| 字段 | 默认 | 含义 |
| --- | --- | --- |
| `YUANTUS_CIRCUIT_BREAKER_CAD_ML_ENABLED` | `false` | 总开关 |
| `YUANTUS_CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD` | `5` | 滚动窗口内失败次数到此即开路 |
| `YUANTUS_CIRCUIT_BREAKER_CAD_ML_WINDOW_SECONDS` | `60` | 失败计数滚动窗口（秒） |
| `YUANTUS_CIRCUIT_BREAKER_CAD_ML_RECOVERY_SECONDS` | `30` | 开路后多少秒进入半开试探 |
| `YUANTUS_CIRCUIT_BREAKER_CAD_ML_HALF_OPEN_MAX_CALLS` | `1` | 半开期允许同时发出的试探调用数 |
| `YUANTUS_CIRCUIT_BREAKER_CAD_ML_BACKOFF_MAX_SECONDS` | `600` | 重复触发开路时指数退避的上限 |

### 状态查询

```bash
curl -s http://127.0.0.1:7910/api/v1/health/deps \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.external.cad_ml.breaker'
```

Prometheus 告警（与 §6 同形）：

```promql
yuantus_circuit_breaker_state{name="cad_ml",state="open"} == 1

rate(yuantus_circuit_breaker_short_circuited_total{name="cad_ml"}[5m]) > 1
```

### 故障处理

完全沿用 §6 的流程；上游 health 端点为
`http://<cad-ml-host>:8001/api/v1/health`。紧急关断点：
`YUANTUS_CIRCUIT_BREAKER_CAD_ML_ENABLED=false` 重启服务。
