# 设计文档：并行支线 P2 Version Checkout Doc-Sync Gate Scope Extension

- 日期：2026-03-06
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：将 checkout 门禁从 item 粒度扩展到 version/file 粒度。

## 1. 目标

1. checkout 前可按 `version + files` 范围评估同步积压，减少 item 级误阻断。
2. 保持兼容：未提供范围时回退 item 粒度。
3. 在阻断结果中回传 `monitored/matched` 文档集合，提升可解释性。

## 2. 方案

## 2.1 服务层

文件：`src/yuantus/meta_engine/services/parallel_tasks_service.py`

扩展 `evaluate_checkout_sync_gate(...)`：

1. 新增入参
- `version_id`
- `document_ids`

2. 粒度策略
- 若传入 `document_ids`：按文档范围评估；
- 若未传入：回退 `item_id` 粒度；
- `version_id` 会被纳入监控集合。

3. 输出增强
- `monitored_document_ids`
- `matched_document_ids`
- 每个 `blocking_job` 增加 `matched_document_ids`。

## 2.2 路由层

文件：`src/yuantus/meta_engine/web/version_router.py`

在 `POST /api/v1/versions/items/{item_id}/checkout` 扩展参数：
- `doc_sync_document_ids`（可选）

并自动聚合 gate 文档集合：
1. 显式 `doc_sync_document_ids`
2. `version_id`
3. `version.primary_file_id`
4. `version.version_files[].file_id`
5. 若集合为空则回退 `item_id`

## 3. 兼容性

1. 不改变默认 checkout 行为（未启用门禁参数时保持原样）。
2. 无数据库迁移。
3. 仅扩展门禁查询逻辑与返回上下文。

## 4. 风险与缓解

1. 风险：version 附件映射遗漏导致漏拦截。
2. 缓解：合并 `primary_file_id + version_files`，并保留 `item_id` 回退路径。
3. 风险：文档范围过宽导致误拦截。
4. 缓解：支持显式 `doc_sync_document_ids` 精准指定。

## 5. 验收标准

1. 支持 version/file 范围门禁。
2. 支持 item 级回退。
3. 阻断上下文可观测（monitored/matched）。
4. 服务与路由测试覆盖通过。
