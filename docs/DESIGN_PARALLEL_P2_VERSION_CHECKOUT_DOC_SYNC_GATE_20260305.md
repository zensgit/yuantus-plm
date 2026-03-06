# 设计文档：并行支线 P2 Version Checkout Doc-Sync Gate

- 日期：2026-03-05
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：在版本 `checkout` 前引入 Doc-Sync 门禁，阻断未同步积压导致的并发设计风险。

## 1. 目标

1. 在工程师 checkout 前检测站点同步积压（pending/processing/failed）。
2. 对阻断原因给出结构化上下文，便于值班快速处理。
3. 保持现有 checkout 路径兼容：仅当传入站点门禁参数时启用。

## 2. 方案

## 2.1 服务层

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

在 `DocumentMultiSiteService` 新增：

1. `evaluate_checkout_sync_gate(...)`
- 入参：`item_id/site_id/window_days/limit`
- 查询窗口内 Doc-Sync 任务，并按 `site_id + document_ids(item_id)` 过滤。
- 阻断条件：任务状态属于 `pending/processing/failed`。
- 附加统计：`dead_letter` 单独计数。
- 返回：`blocking/blocking_total/blocking_counts/blocking_jobs`。

## 2.2 路由层

文件：`src/yuantus/meta_engine/web/version_router.py`

改造接口：
- `POST /api/v1/versions/items/{item_id}/checkout`

新增可选 body 参数：
- `doc_sync_site_id`
- `doc_sync_window_days`（默认 7）
- `doc_sync_limit`（默认 200）

行为：
1. 若提供 `doc_sync_site_id`，先执行门禁评估。
2. 门禁参数非法：返回 `400`，错误码 `doc_sync_checkout_gate_invalid`。
3. 有阻断任务：返回 `409`，错误码 `doc_sync_checkout_blocked`。
4. 无阻断：继续既有 `VersionService.checkout` 逻辑。

## 3. 兼容性

1. 默认不启用门禁（不传 `doc_sync_site_id` 时行为不变）。
2. 无数据库迁移。
3. 对既有客户端完全向后兼容。

## 4. 风险与缓解

1. 风险：document_id 与 item_id 映射不一致导致误阻断。
2. 缓解：先采用显式 `document_ids` 匹配，后续可扩展映射策略。
3. 风险：大窗口查询可能带来路由延时。
4. 缓解：增加 `window_days/limit` 上限并按 created_at 倒序截断。

## 5. 验收标准

1. 门禁开启时能阻断存在同步积压的 checkout。
2. 门禁关闭时 checkout 行为不变。
3. 错误码和上下文结构化可读。
4. 服务层与路由层测试通过。
