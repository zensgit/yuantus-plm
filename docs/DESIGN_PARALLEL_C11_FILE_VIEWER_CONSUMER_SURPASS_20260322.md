# C11 – File/3D Viewer Consumer 超越设计（2026-03-22）

## 1. 目标

在已有 `consumer-summary`、`viewer-readiness/export`、`geometry-pack-summary` 的基础上，补齐对标对照以后的“可审计、可追溯、可运维”能力：

- 统一批量参数校验（长度、空值、类型）
- 为单文件/批量结果补充审计证明（review + 变更历史摘要）
- 增加可选 reviewer profile 与历史回看深度
- 批量导出 CSV 增加可观察字段
- 维持现有向后兼容（默认关闭审计开销）
- 导出与汇总返回强化：`not_found_count`、`requested_file_count`、`generated_at`

## 2. API 变更

### GET `/file/{file_id}/consumer-summary`

- 新增 Query 参数
  - `include_audit: bool = false`
  - `history_limit: int = 3`（1-200）
  - `include_reviewer_profile: bool = false`
- 新增返回段：
  - `proof`:
    - `review`: `state / note / reviewed_at / reviewed_by`
    - `review_api`: `/api/v1/cad/files/{file_id}/review`
    - `history_api`: `/api/v1/cad/files/{file_id}/history`
    - `audit`: `{enabled, history_count, latest, history?}`
- 默认关闭审计时：`audit.enabled = false`，不查询 `CadChangeLog`。

### POST `/file/viewer-readiness/export`

- 请求体改为结构化 `C11BatchRequest`：`{"file_ids": [...]}`。
- 新增 Query 参数（与单文件一致）：
  - `include_audit`
  - `history_limit`
  - `include_reviewer_profile`
- JSON 模式在每个 `files[]` 项加入：
  - `found`、`asset_count`、`available_assets`、`proof`。
- CSV 模式新增字段：
  - `found`、`asset_count`、`review_state`、`reviewed_by`、`reviewed_at`、`history_count`、`history_latest_action`
- JSON 模式新增字段：
  - `not_found_count`、`requested_file_count`、`generated_at`
- `export_format` 支持大小写不敏感（例如 `CSV`）。

### POST `/file/geometry-pack-summary`

- 请求体改为 `C11BatchRequest`。
- 新增 Query 参数：
  - `include_audit`
  - `history_limit`
  - `include_reviewer_profile`
  - `include_assets`（默认 true；可用于减小批量 payload）
- 返回新增：
  - 每个 `pack[]` 项 `proof`
  - `audited_files`
  - `generated_at`
  - `not_found_count`

## 3. 审计与安全边界

- 审计历史通过 `CadChangeLog` 查询并按时间倒序返回，最多 `history_limit` 条。
- 当 `include_reviewer_profile=true` 时尝试读取身份数据库补齐 `user_id / username / email`。
- 访问 identity DB 失败时降级为仅返回 `{"id": reviewer_id}`，保持接口可用。
- 批量上限固定为 200，避免大请求引发内存和 DB 压力。

## 4. 实现点

- `src/yuantus/meta_engine/web/file_router.py`
  - 新增 `C11BatchRequest`、`C11_MAX_BATCH_FILE_IDS`、`C11_DEFAULT_AUDIT_HISTORY_LIMIT`
  - 新增 `/_normalize_batch_file_ids`、`/_resolve_reviewer_identity`、`/_load_file_change_log_history`、`/_build_c11_consumer_proof`、`/_build_c11_export_row`
  - 增强 3 个 C11 路由参数/返回结构

- 关键设计取舍
  - 默认不返回完整审计，优先保证吞吐。
  - 在 `viewer-readiness/export` 的 CSV 与 JSON 返回中兼容旧字段，新增字段仅向前兼容追加，不移除旧字段。

## 5. 验证点（需执行）

- `export_format=csv` 时新增审计列是否存在且可解析
- `include_audit=true` 是否返回 `proof.audit.enabled=true` 与 `history_count`
- `history_limit` 是否约束历史数量
- `file_ids` 201 条是否拒绝，空列表是否拒绝
- `export_format` 大小写是否兼容（`CSV`）
- `requested_file_count`、`not_found_count`、`generated_at` 是否返回
- `include_assets=false` 时几何资产列表不返回完整 asset 内容
