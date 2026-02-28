# 并行支线任务建议（基于参考库 odoo18-enterprise-main）

- 参考库：`/Users/huazhou/Downloads/Github/Yuantus/references/odoo18-enterprise-main`
- 评估时间：`2026-02-27`
- 目标：识别可在当前 `Yuantus` 主线外并行推进、且与现有能力互补的功能。

## 一、已存在能力（建议不作为新支线重复开发）

- `Pack and Go`：当前仓库已有插件能力与测试（例如 `src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py`）。
- `Suspended/Latest`：当前生命周期与版本体系已有 suspended / latest 语义。
- `3D/CAD 基础能力`：已有 CAD 路由、转换与 3D 文件类型支持。

## 二、可并行支线任务池（建议）

## P0-A：多站点文档同步（Document Multi-Site）
- 参考模块：
  - `addons/plm_document_multi_site/models/plm_remote_server.py`
  - `addons/plm_document_multi_site/models/plm_document_action_syncronize.py`
- 适合并行原因：与现有核心 BOM/版本主链路耦合低，可独立成“同步子系统”。
- 建议交付：
  - `remote_site` 配置模型（endpoint、认证、启停、健康状态）
  - `document_sync_job` 队列模型（push/pull、重试、失败原因、幂等键）
  - Worker 任务与 API：手动同步、批量同步、状态查询
  - 最小安全基线：密钥加密存储、超时/重试/退避、失败隔离
  - E2E：双站点样例（A->B push + B->A pull）
- 依赖：对象存储抽象、任务队列（当前已有）
- 建议分支：`codex/feature-doc-multi-site-sync`

## P0-B：ECR/ECO 活动网关（Activity Validation）
- 参考模块：
  - `addons/activity_validation/models/mail_activity.py`
- 适合并行原因：流程状态机独立，可与当前 ECO 流程增强并行。
- 建议交付：
  - 活动依赖 DAG（父子任务、并行/串行、阻塞条件）
  - 状态机约束（禁止未完成子任务直接关闭父任务）
  - 审批可追溯（操作日志 + 状态变更事件）
  - API：创建依赖任务、推进状态、阻塞原因查询
  - 回归：异常状态（cancel/exception）与恢复路径
- 依赖：ECO/工作流基础实体（当前已有）
- 建议分支：`codex/feature-eco-activity-validation`

## P0-C：工作流自定义动作引擎（Workflow Custom Actions）
- 参考模块：
  - `addons/plm_workflow_custom_action/models/plm_automated_wf_actions.py`
- 适合并行原因：事件钩子层可作为平台扩展点，不与业务域强耦合。
- 建议交付：
  - `before/after transition` 钩子注册机制
  - 动作执行器（白名单动作、参数模板、上下文注入）
  - 失败策略（阻断/告警/重试）与审计记录
  - 最小 DSL/规则（目标对象、from_state、to_state、domain）
- 依赖：现有 workflow 引擎
- 建议分支：`codex/feature-workflow-custom-actions`

## P1-D：BOM 对比增强（Compare BOM）
- 参考模块：
  - `addons/plm_compare_bom/wizard/compare_bom.py`
- 适合并行原因：计算逻辑可独立服务化，对 UI/API 的影响可后置。
- 建议交付：
  - 多比较模式：
    - 仅存在性（only_product）
    - 位号+数量（num_qty）
    - 汇总数量（summarized）
  - 差异补丁（apply delta）与预览
  - 差异导出（CSV/JSON）
- 依赖：现有 BOM 服务
- 建议分支：`codex/feature-bom-compare-modes`

## P1-E：消耗计划（Consumption Plans）
- 参考模块：
  - `addons/plm_consumption_plans/models/template_consumption_plan.py`
  - `addons/plm_consumption_plans/models/consumption_state.py`
- 适合并行原因：偏制造运营指标，和核心对象模型松耦合。
- 建议交付：
  - 计划模板（时段、状态、适用物料/模板）
  - 实际消耗回写接口（工单/报工事件）
  - 偏差分析（计划 vs 实际）
  - 简版看板/API
- 依赖：制造执行数据采集
- 建议分支：`codex/feature-consumption-plans`

## P1-F：质量异常与工单联动（Breakages + Helpdesk）
- 参考模块：
  - `addons/plm_breakages/models/breakages.py`
  - `addons/plm_ent_breakages_helpdesk/models/helpdesk_ticket.py`
- 适合并行原因：可先做核心异常闭环，再接入客服/工单系统。
- 建议交付：
  - `breakage` 事件模型（产品/批次/客户/描述/责任）
  - 关联对象：BOM 行、生产单、版本
  - 工单联动接口（可先 stub）
  - 指标：重复故障率、故障热力部件
- 依赖：产品/BOM/生产对象
- 建议分支：`codex/feature-breakage-incident-loop`

## P2-G：生产工单文档包（PDF Workorder Docs）
- 参考模块：
  - `addons/plm_pdf_workorder/models/mrp_workorder.py`
  - `addons/plm_pdf_workorder/models/mrp_routing_workcenter.py`
- 适合并行原因：主要是文档聚合与渲染，不影响核心事务模型。
- 建议交付：
  - 工单关联 PLM 文档筛选（生产可见文档）
  - 工单文档包导出（PDF/ZIP）
  - 工序级文档继承规则
- 依赖：文档关联关系
- 建议分支：`codex/feature-workorder-doc-pack`

## P2-H：3D 预览信息增强（Web3D Metadata Overlay）
- 参考模块：
  - `addons/plm_web_3d/controllers/main.py`
  - `addons/plm_web_3d/models/product_product_document_rel.py`
- 适合并行原因：前端展示增强，可与后端并行开发。
- 建议交付：
  - 3D 查看器侧边栏（编码/版本/状态/关联部件）
  - 组件点击回查（viewer -> item/document API）
  - 权限收敛（仅授权用户可见）
- 依赖：当前 CAD/3D API
- 建议分支：`codex/feature-3d-metadata-overlay`

## 三、建议并发编组（可立即开工）

- 小组 1（平台流程）
  - P0-B `activity validation`
  - P0-C `workflow custom actions`
- 小组 2（文档与集成）
  - P0-A `multi-site sync`
- 小组 3（制造质量）
  - P1-D `BOM compare enhanced`
  - P1-F `breakage loop`

说明：以上 3 组互相冲突低，可并发推进；P2 任务可在 P0/P1 稳定后插入。

## 四、优先执行建议（1 周）

1. 先落地 P0-A + P0-B + P0-C 的最小可用版本（MVP）。
2. P1-D 并行开发“只读差异”与“差异导出”，暂不开放自动写回。
3. P1-F 先做异常数据模型和报表，不阻塞 helpdesk 正式接入。

## 五、并行开发落地清单（可直接分配）

### Track-1：流程平台（P0-B + P0-C）
- 任务 T1.1：活动依赖 DAG 与阻塞校验
  - 输出：依赖关系模型、状态推进约束、阻塞原因查询 API
  - 验收：覆盖串行/并行/异常恢复 3 类回归用例
- 任务 T1.2：工作流 transition 钩子和动作执行器
  - 输出：`before/after` 钩子、白名单动作、审计日志
  - 验收：动作成功、动作失败阻断、动作失败重试三条路径稳定
- 任务 T1.3：流程观测能力
  - 输出：状态迁移事件日志与查询接口
  - 验收：任意对象可追溯最近 20 次状态流转

### Track-2：文档集成（P0-A）
- 任务 T2.1：远端站点配置与健康检查
  - 输出：`remote_site` 配置模型、认证配置、连通性探测
  - 验收：至少 2 个远端配置可独立启停，健康状态可查询
- 任务 T2.2：同步任务模型与幂等机制
  - 输出：`document_sync_job`、幂等键、失败重试与退避
  - 验收：重复触发不产生重复同步，失败任务可重放
- 任务 T2.3：双向同步最小闭环
  - 输出：A->B push 与 B->A pull 样例流程
  - 验收：样例文档元数据与文件内容一致

### Track-3：制造质量（P1-D + P1-F）
- 任务 T3.1：BOM 多模式对比引擎
  - 输出：`only_product` / `num_qty` / `summarized` 三模式
  - 验收：对比结果可稳定导出 CSV/JSON
- 任务 T3.2：差异补丁预览（只读阶段）
  - 输出：delta 预览 API，不直接写回
  - 验收：补丁预览与导出结果一致
- 任务 T3.3：质量异常事件模型
  - 输出：`breakage` 模型与关联 BOM/生产/版本能力
  - 验收：可按产品、批次、部件聚合查询异常

## 六、Definition of Done（每个支线统一标准）

- 代码：核心功能 + 异常路径处理 + 幂等/重试或阻塞策略。
- 测试：至少包含单测与集成测试；新增能力必须有失败场景回归。
- 文档：接口说明、状态机/同步时序说明、运维参数说明。
- 观测：关键事件有日志字段，支持排查（对象 ID、动作、结果、错误码）。
- 回滚：明确开关/降级路径，出现故障可关闭新能力并保持主流程可用。

## 七、统一验证基线（建议所有支线都执行）

1. 单元与集成测试
   - `pytest -q`
2. CI 合同测试（如涉及 workflow 变更）
   - `pytest -q src/yuantus/meta_engine/tests`
3. 关键路径冒烟
   - 对应支线至少 1 条成功路径 + 1 条失败恢复路径
4. 回归结论文档
   - 每条支线新增 `docs/verification-<track>-<date>.md`

## 八、建议并行排期（10 个工作日）

1. Day 1-2
   - Track-1 完成 DAG/钩子骨架
   - Track-2 完成站点配置与健康检查
   - Track-3 完成 BOM 对比多模式框架
2. Day 3-6
   - Track-1 完成动作执行器与审计
   - Track-2 完成同步任务队列与幂等
   - Track-3 完成差异导出与异常模型
3. Day 7-8
   - 三条支线联调与失败路径验证
4. Day 9-10
   - 文档、回归、合并准备（按风险从低到高分批合并）

## 九、完成状态（已落地）

- [x] P0-A 多站点文档同步（含 A->B push / B->A pull 样例验证）
- [x] P0-B ECO 活动网关（阻塞校验 + 事件追踪）
- [x] P0-C 工作流自定义动作（before/after hooks + 执行记录）
- [x] P1-D BOM 差异补丁预览与导出（JSON/CSV）
- [x] P1-E 消耗计划（计划/实际/偏差/看板）
- [x] P1-F 质量异常闭环（指标 + helpdesk stub 联动）
- [x] P2-G 工单文档包（继承规则 + PDF/ZIP 导出）
- [x] P2-H 3D 元数据叠加（角色可见 + 组件回查）

最终验证：`pytest -q src/yuantus/meta_engine/tests` -> `73 passed`。
