# 并行开发下一阶段 Backlog（含验收标准）

- 日期：2026-02-28
- 仓库：`/Users/huazhou/Downloads/Github/Yuantus`
- 基线：并行支线已完成首轮全量交付，`meta_engine` 回归 `73 passed`，CI/Regression 均为 `success`。
- 目标：在不破坏现有主流程的前提下，推进稳定性、可观测性、可运维性与业务深度。

## 1. 并行编组

1. Track-A（平台流程）
- ECO/Workflow 规则能力增强与治理。

2. Track-B（文档与同步）
- 多站点同步可靠性与导出链路增强。

3. Track-C（制造质量）
- BOM 差异与 Breakage 闭环的数据化、报表化。

## 2. P0 清单（高优先级，先做）

### P0-1 同步任务可靠性升级（Track-B）

- 范围：
  - 为文档同步增加退避重试上限、死信标记、幂等冲突诊断字段。
  - 增加同步任务可观测字段（trace_id、origin_site、payload_hash）。
- 代码点：
  - `parallel_tasks_service.py`
  - `parallel_tasks_router.py`
- 验收标准：
  - 同一幂等键重复提交不产生重复生效任务。
  - 失败重试达到上限后进入终态，且可审计失败原因。
  - 提供任务过滤查询（按站点、状态、时间窗）。
- 验证：
  - 新增集成测试覆盖重复提交、指数退避、死信终态。
  - `pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`

### P0-2 Workflow 动作执行治理（Track-A）

- 范围：
  - 增加规则冲突检测（同对象同 transition 重复规则优先级）。
  - 增加动作超时控制和最大重试保护。
  - 标准化执行结果码（OK/WARN/BLOCK/RETRY_EXHAUSTED）。
- 代码点：
  - `parallel_tasks_service.py`
  - `eco_service.py`
- 验收标准：
  - 冲突规则可被识别并给出 deterministic 执行顺序。
  - `fail_strategy=block` 的失败路径不会留下半提交状态。
  - 超时动作进入受控失败并写入运行记录。
- 验证：
  - 新增规则冲突、超时、回滚用例。
  - `pytest -q src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

### P0-3 API 错误合同统一（Track-A + Track-B）

- 范围：
  - 统一并行支线路由的异常结构与错误码映射。
  - 补齐文档与测试对错误体字段的断言。
- 代码点：
  - `parallel_tasks_router.py`
  - `test_parallel_tasks_router.py`
- 验收标准：
  - 关键错误场景返回稳定错误码、消息和上下文字段。
  - 已有客户端调用不需修改即可识别失败类型。
- 验证：
  - API 合同回归全部通过。
  - `pytest -q src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`

## 3. P1 清单（中优先级，P0 稳定后并行）

### P1-1 BOM Delta 导出扩展（Track-C）

- 范围：
  - 为 delta 导出增加变更摘要（新增/删除/更新计数、风险分级）。
  - 增加可选字段过滤导出。
- 代码点：
  - `bom_service.py`
  - `bom_router.py`
- 验收标准：
  - 导出结果与预览数据严格一致。
  - 摘要统计与逐项差异数量一致。
- 验证：
  - `test_bom_delta_preview.py` 增加摘要一致性断言。

### P1-2 Breakage 指标面板 API（Track-C）

- 范围：
  - 增加按产品/批次/责任组织维度聚合查询。
  - 增加趋势窗口（7/14/30 天）输出。
- 代码点：
  - `parallel_tasks_service.py`
  - `parallel_tasks_router.py`
- 验收标准：
  - 支持多维过滤与分页。
  - 趋势统计在空数据与边界数据下稳定。
- 验证：
  - 新增指标 API 测试及边界用例。

### P1-3 Workorder PDF 导出质量提升（Track-B）

- 范围：
  - 优化 PDF 摘要内容结构（文档分类、操作步骤、版本信息）。
  - 增加导出元数据（生成时间、工单号、操作者）。
- 代码点：
  - `parallel_tasks_router.py`
  - `test_parallel_tasks_router.py`
- 验收标准：
  - PDF 导出稳定、内容字段完整。
  - `zip/json/pdf` 三格式行为一致且错误处理统一。
- 验证：
  - 路由测试扩展到导出内容结构断言。

## 4. P2 清单（低优先级，持续迭代）

### P2-1 3D Overlay 查询性能与缓存（Track-B）

- 范围：
  - 热点 overlay 查询缓存策略。
  - 组件回查批量接口。
- 验收标准：
  - 常见读取路径响应显著下降（以基线为对照）。
  - 批量查询结果与单条查询一致。
- 验证：
  - 新增性能 smoke 脚本与一致性测试。

### P2-2 消耗计划策略模板化（Track-C）

- 范围：
  - 增加模板版本管理和启停策略。
  - 增加计划变更影响预览。
- 验收标准：
  - 模板切换不会破坏历史记录。
  - 计划变更前可预览影响范围。
- 验证：
  - 新增模板切换与回滚测试。

### P2-3 观测与运维 Runbook（跨 Track）

- 范围：
  - 为并行支线补齐 SLI/SLO 指标建议与排障流程。
  - 固化常见故障处理手册。
- 验收标准：
  - 关键故障场景有明确操作步骤与回滚路径。
  - 文档可直接用于值班交接。
- 验证：
  - 通过一次演练记录验证 runbook 可执行性。

## 5. 每个任务必须产出的设计/验证 MD

1. 设计文档命名：
- `docs/DESIGN_PARALLEL_<TASK>_<YYYYMMDD>.md`

2. 验证文档命名：
- `docs/DEV_AND_VERIFICATION_PARALLEL_<TASK>_<YYYYMMDD>.md`

3. 文档最低内容要求：
- 目标与范围
- 接口/数据模型变更
- 风险与回滚
- 验证命令
- 验证结果（含通过率/失败样例处理）

## 6. 统一 DoD（Definition of Done）

1. 代码完成：成功路径 + 失败路径 + 回滚/降级路径均实现。
2. 测试完成：新增能力必须有单测与至少一条 API/集成测试。
3. 文档完成：设计 + 验证 MD 同步入库。
4. 回归完成：`pytest -q src/yuantus/meta_engine/tests` 无新增失败。
5. CI 完成：`CI` 与 `regression` 均为 `success`。

## 7. 建议执行顺序（可直接开工）

1. P0-1 + P0-2 + P0-3 并行推进并先合入。
2. P1-1 + P1-2 + P1-3 作为第二批并行合入。
3. P2 系列按资源滚动进入，每项单独验收。

