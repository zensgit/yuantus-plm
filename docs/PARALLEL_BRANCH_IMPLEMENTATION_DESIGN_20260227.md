# 并行支线开发设计文档（落地版）

- 日期：2026-02-27
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 目标：按并行支线清单完成 P0/P1/P2 的最小可交付实现，并保持现有主线兼容。

## 1. 设计范围与映射

本次落地覆盖如下支线能力：

1. P0-A 多站点文档同步（Document Multi-Site）
2. P0-B ECO 活动网关（Activity Validation）
3. P0-C 工作流自定义动作（Workflow Custom Actions）
4. P1-D BOM 差异补丁预览与导出（在既有 Compare 基础上增强）
5. P1-E 消耗计划（Consumption Plans）
6. P1-F 质量异常闭环（Breakage）
7. P2-G 工单文档包（Workorder Doc Pack）
8. P2-H 3D 元数据叠加（Web3D Metadata Overlay）

## 2. 架构原则

1. 复用现有基础设施
- 任务队列复用 `meta_conversion_jobs`（通过 `JobService`），不新建重复队列表。
- API 统一挂载到主应用 `create_app()`。

2. 增量式持久化
- 通过新增 `parallel_tasks` 模型承载支线数据。
- 与主线模型弱耦合，避免破坏现有 BOM/ECO/manufacturing 事务。

3. 可回滚与可观测
- 核心流程均提供状态查询与事件/运行记录。
- 动作执行结果与失败原因可追踪。

## 3. 数据模型设计

新增模型文件：
- `src/yuantus/meta_engine/models/parallel_tasks.py`

新增表：

1. `meta_remote_sites`
- 远端站点配置、健康状态、密钥密文（ciphertext）存储。

2. `meta_eco_activity_gates`
- ECO 活动节点、依赖、阻塞与状态。

3. `meta_eco_activity_gate_events`
- ECO 活动状态事件审计（from/to/reason/user）。

4. `meta_workflow_custom_action_rules`
- 工作流规则（before/after、from/to、动作类型、失败策略）。

5. `meta_workflow_custom_action_runs`
- 规则执行记录（状态、尝试次数、错误、结果）。

6. `meta_consumption_plans`
- 计划模板/周期/目标量。

7. `meta_consumption_records`
- 实际消耗记录（来源、数量、时间）。

8. `meta_breakage_incidents`
- 质量异常事件（产品/批次/版本/责任/状态/严重度）。

9. `meta_workorder_document_links`
- 工单文档映射（routing/operation/document，可见性与继承）。

10. `meta_3d_overlays`
- 3D 叠加元数据（版本、状态、组件引用、可见角色）。

迁移文件：
- `migrations/versions/z1b2c3d4e7a5_add_parallel_branch_tables.py`

## 4. 服务层设计

新增服务文件：
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`

包含服务：

1. `DocumentMultiSiteService`
- 站点增删改查（upsert/list/get）
- 健康探测（`/health`）
- 同步任务入队（push/pull，幂等 key）
- 同步任务查询与 replay
- 密钥以轻量对称加密密文存储（避免明文持久化）
- 支持 A->B push / B->A pull 双向样例流程验证

2. `ECOActivityValidationService`
- 活动创建、依赖阻塞校验
- 状态推进（完成前依赖校验）
- 阻塞原因查询
- 最近事件查询

3. `WorkflowCustomActionService`
- 规则创建与查询
- transition 阶段规则匹配与执行
- 白名单动作：
  - `emit_event`
  - `create_job`
  - `set_eco_priority`
- 失败策略：
  - `block`
  - `warn`
  - `retry`

4. `ConsumptionPlanService`
- 计划创建、实际回写、偏差计算、看板聚合

5. `BreakageIncidentService`
- 异常创建/查询/状态更新
- 指标计算：重复故障率、热点部件
- helpdesk 联动 stub：通过异步任务 `breakage_helpdesk_sync_stub` 对接外部工单

6. `WorkorderDocumentPackService`
- 文档链接 upsert
- 继承逻辑查询（routing 级继承到 operation）
- 文档包导出（manifest + csv -> zip）

7. `ThreeDOverlayService`
- overlay upsert/get
- 基于角色的可见性限制
- 组件点击回查（component_ref -> 对应对象）

## 5. API 设计

新增路由文件：
- `src/yuantus/meta_engine/web/parallel_tasks_router.py`

主入口注册：
- `src/yuantus/api/app.py`（新增 `parallel_tasks_router`）

主要接口组：

1. `/api/v1/doc-sync/*`
- 站点配置、健康检查、同步任务创建/查询/replay

2. `/api/v1/eco-activities/*`
- 活动创建、列表、状态迁移、阻塞、事件

3. `/api/v1/workflow-actions/*`
- 规则创建/查询、动作执行

4. `/api/v1/consumption/*`
- 计划、实际、偏差、看板

5. `/api/v1/breakages/*`
- 异常事件与指标
- `POST /api/v1/breakages/{incident_id}/helpdesk-sync`（stub 联动）

6. `/api/v1/workorder-docs/*`
- 链接维护、文档包导出

7. `/api/v1/cad-3d/overlays/*`
- overlay 管理与组件回查

## 6. BOM 增强设计（P1-D）

增强文件：
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`

新增能力：

1. `build_delta_preview(compare_result)`
- 将 compare 输出转为只读 delta patch（add/remove/update）

2. `export_delta_csv(delta_preview)`
- 导出 CSV 结构用于审阅/审批

3. 新增接口
- `GET /api/v1/bom/compare/delta/preview`
- `GET /api/v1/bom/compare/delta/export?export_format=json|csv`

## 7. 主流程接入补充（继续开发阶段）

为避免并行能力“只可单独调用”，本轮将关键能力接入 ECO 主流程：

1. 接入点
- 文件：`src/yuantus/meta_engine/services/eco_service.py`
- 方法：`move_to_stage`、`action_apply`

2. 接入规则
- 在关键状态迁移前执行活动网关阻塞校验（`_ensure_activity_gate_ready`）。
- 在状态迁移前后执行自定义动作引擎（`_run_custom_actions`，before/after）。

3. 运行语义
- 若活动阻塞未解除，迁移被拒绝并返回明确 blocker 信息。
- 若自定义动作规则 `fail_strategy=block` 且失败，迁移中止并回滚。
- `warn/retry` 按规则降级执行，不阻塞主流程。

## 8. 兼容性与风险控制

1. 不修改既有核心表语义，仅新增表与路由。
2. 新增功能默认按需调用，不影响现有主链路执行。
3. 所有写接口均在异常时 rollback，避免脏事务。
4. 复用既有 JobService，减少并发/重试逻辑重复实现风险。
