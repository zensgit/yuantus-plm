# 设计文档：并行支线 P2（3D Overlay 缓存与批量回查 + 消耗模板版本化 + 观测运维）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 范围：`P2-1 + P2-2 + P2-3`

## 1. 目标与范围

1. `P2-1` 3D Overlay 查询性能增强：为热点读取路径引入内存缓存，并提供批量组件回查接口。
2. `P2-2` 消耗计划模板化：支持模板版本创建、版本列表、启停切换、变更影响预览。
3. `P2-3` 观测与运维：沉淀并行支线的 SLI/SLO 与排障操作流程，形成可交接 Runbook。

## 2. 设计方案

## 2.1 P2-1 3D Overlay 缓存与批量回查

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

### 关键点

1. 服务层新增缓存机制（`ThreeDOverlayService`）：
- 基于进程内字典 + `Lock` 线程安全。
- TTL：60 秒。
- 容量上限：500 条，超限按最早写入逐出。
- 指标：`hits/misses/evictions/entries`。

2. 缓存一致性：
- `upsert_overlay` 成功后执行 `invalidate + set`，避免旧数据持续命中。
- 读取路径 `get_overlay` 先查缓存，未命中才读 DB 并回填。

3. 批量组件回查：
- 新增 `resolve_components`（单文档、多 `component_ref`）。
- 输出包含 `requested/returned/hits/misses/results`。
- 支持 `include_missing` 控制是否返回未命中项。

4. 新增接口：
- `GET /api/v1/cad-3d/overlays/cache/stats`
- `POST /api/v1/cad-3d/overlays/{document_item_id}/components/resolve-batch`

## 2.2 P2-2 消耗计划模板版本化

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/parallel_tasks_router.py`

### 关键点

1. 模板版本元信息模型（复用 `ConsumptionPlan.properties.template`）：
- `key`
- `version`
- `is_template_version`
- `is_active`

2. 版本管理能力：
- 创建模板版本：可自动生成版本号（默认 `vN`）。
- 激活切换：同一模板仅允许一个活动版本，激活时自动失活其余版本。
- 版本列表：支持 `include_inactive`。

3. 影响预览：
- 输入候选计划量，输出对各版本的数量影响及汇总。
- 汇总包括 `baseline_quantity/candidate_quantity/delta_quantity`。

4. 新增接口：
- `POST /api/v1/consumption/templates/{template_key}/versions`
- `GET /api/v1/consumption/templates/{template_key}/versions`
- `POST /api/v1/consumption/templates/versions/{plan_id}/state`
- `POST /api/v1/consumption/templates/{template_key}/impact-preview`

5. 错误合同：
- `consumption_template_version_invalid`
- `consumption_template_version_not_found`
- `consumption_template_preview_invalid`

## 2.3 P2-3 观测与运维 Runbook

文件：
- `/Users/huazhou/Downloads/Github/Yuantus/docs/RUNBOOK_PARALLEL_BRANCH_OBSERVABILITY_20260228.md`

### 关键点

1. 定义并行支线关键 SLI：
- 3D overlay 缓存命中率与逐出率。
- 模板版本切换成功率与切换耗时。
- 模板影响预览稳定性（错误率）。

2. 定义值班排障流程：
- 读路径性能异常。
- 模板切换失败。
- 影响预览结果异常。

3. 定义回滚策略：
- API 降级到单条回查。
- 停用模板版本化入口。
- 保持已有 plan/overlay 历史数据不丢失。

## 3. 数据模型与兼容性

1. 不新增数据库迁移。
2. 模板版本化复用 `ConsumptionPlan` 与 `properties.template`。
3. overlay 缓存为进程内态，不改变持久化数据结构。

## 4. 风险与回滚

1. 风险：缓存可能在 TTL 窗口内保留旧数据。
- 控制：写路径主动失效；TTL 短周期；可观察缓存指标。

2. 风险：模板版本激活冲突导致状态不一致。
- 控制：激活动作内统一串行更新同模板版本状态。

3. 回滚：
- 路由层停止新接口暴露，不影响原有 `consumption/plans` 与 `cad-3d` 单条查询。

## 5. 验收标准

1. 批量组件回查结果与单条回查一致。
2. 模板激活切换可保证单模板只有一个活动版本。
3. 影响预览输出基线版本与差值汇总正确。
4. Runbook 可覆盖常见值班故障处置。
