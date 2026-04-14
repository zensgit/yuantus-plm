# Runbook: CAD Legacy Conversion Queue Audit

目标：对 legacy CAD conversion queue 的数据面和代码引用面做一次可重复审计，并输出证据目录。它既适用于删除 `cad_conversion_jobs` dual-read fallback 之前的 readiness 评估，也适用于物理表删除后的稳态复核。

## 1. 适用范围

- 适用于仍保留 dual-read fallback 的版本
- 也适用于物理 `cad_conversion_jobs` 表已删除、只需要确认 post-removal steady state 的版本
- 本 runbook 只做审计，不做数据修改
- 适用于：
  - 单租户
  - `db-per-tenant`
  - `db-per-tenant-org`

## 2. 前置检查

- 确认版本已包含 `scripts/audit_legacy_cad_conversion_jobs.py`
- 确认业务侧主写路径已经切到 canonical `meta_conversion_jobs`
- 确认目标库可连接

## 3. 证据目录

```bash
TS=$(date +%Y%m%d_%H%M%S)
OUT="tmp/cad-legacy-conversion-queue-audit/${TS}"
mkdir -p "$OUT"
```

输出内容：

- `summary.json`
- `jobs.jsonl`
- `pending.jsonl`
- `anomalies.jsonl`
- `samples.json`
- `code_references.jsonl`

## 4. Dry-run 审计

### 4.1 单租户

```bash
python3 scripts/audit_legacy_cad_conversion_jobs.py \
  --out-dir "$OUT" \
  --json-out "$OUT/report.json"
```

### 4.2 多租户

```bash
python3 scripts/audit_legacy_cad_conversion_jobs.py \
  --tenant <tenant> \
  --org <org> \
  --out-dir "$OUT" \
  --json-out "$OUT/report.json"
```

## 5. 结果判定

重点检查：

- `summary.json`
  - `legacy_table_present`
  - `job_count`
  - `active_job_count`
  - `counts_by_status`
  - `counts_by_flag`
  - `legacy_queue_drain_complete`
  - `legacy_dual_read_zero_rows`
  - `code_reference_count`
  - `code_reference_counts_by_scope`
  - `delete_window_ready`
- `pending.jsonl`
  - 是否仍有 `pending/processing`
- `anomalies.jsonl`
  - 是否存在 `missing_source_file`
  - 是否存在 `missing_result_file`
  - 是否存在 `completed_without_result`
  - 是否存在 `failed_without_error`
- `code_references.jsonl`
  - 是否仍有 `production` scope 的 legacy 引用

建议判定：

- `legacy_table_present == false`
  - 在 post-removal steady state 下是合法结果，不应单独视为异常
- `legacy_table_present == true`
  - 说明库里仍有 legacy 物理表，需要继续结合 `job_count/active_job_count` 判断是否可删表
- `active_job_count == 0`
  - 说明 legacy 队列已排空
- `job_count == 0`
  - 说明 legacy 数据面具备删除前提；在 `legacy_table_present == false` 时也应自然成立
- `code_reference_counts_by_scope.production == 0`
  - 说明生产代码面具备删除前提
- 上述条件满足时，才建议把 `delete_window_ready` 当成 `true`

## 6. 后续动作

- 如果 `active_job_count > 0`
  - 暂不考虑删除 dual-read
- 如果 `anomalies.jsonl` 非空
  - 先排查历史残缺 job，再评估 cleanup
- 如果 `code_references.jsonl` 仍包含生产引用
  - 先收口调用面，再评估下线窗口
- 如果 `delete_window_ready == true`
  - pre-removal：可以进入 fallback 删除评估窗口
  - post-removal：说明删除后的 steady state 仍满足审计约束

## 7. 注意事项

- 这个脚本不提供 apply 模式
- 它不会自动改库，也不会自动 drop legacy 表
- 当 `legacy_table_present == false` 时，脚本仍会继续审计代码引用面，并把“表不存在”视为有效稳态
- 它只负责审计 `cad_conversion_jobs` 的数据面和代码引用面
- 真正删除 dual-read 仍需结合业务回归和 caller 观察结果判断
