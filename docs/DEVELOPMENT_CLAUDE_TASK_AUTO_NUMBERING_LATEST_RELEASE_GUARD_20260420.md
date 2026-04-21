# Claude 开发任务书：自动编号 + 最新已发布版本约束（2026-04-20）

## 1. 目标

给 Claude Code CLI 一个边界明确的首个 Odoo18 对标增量，只做两件事：

1. Part / Document 等 Item 新建时的自动部件编号 / 内部编码。
2. BOM / Substitute / Effectivity 写路径上的“仅最新已发布版本可被下游消费”约束。

本任务完成后，应能把 `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` 中 ROI 最高的第一块能力，从“分析建议”推进到“可审阅 PR”。

## 2. 重要前提

- 以当前主干代码为准，不以历史 gap 文档的逐字描述为准。
- 本任务是 bounded increment，不顺手推进 `Suspended`、scheduler、outbox、router 大拆分、UI 大改。
- 允许最小必要 schema/migration，但不要为了“以后也许有用”做大而全设计。
- 先做后端主线；前端只允许最小只读展示或 contract 对齐，不做工作台重构。
- 保持现有权限模型、租户/org 语义、版本主链、P1/P2 主线能力不回归。

## 3. 当前代码入口

Claude 落地前先阅读这些真实入口，不要凭 gap 文档猜路径：

- ItemType / Property 模型：`src/yuantus/meta_engine/models/meta_schema.py`
- Item 模型：`src/yuantus/meta_engine/models/item.py`
- AML 入口：`src/yuantus/meta_engine/services/engine.py`
- Item add 主路径：`src/yuantus/meta_engine/operations/add_op.py`
- BOM 写路径：`src/yuantus/meta_engine/services/bom_service.py`
- BOM Router：`src/yuantus/meta_engine/web/bom_router.py`
- Effectivity 写路径：`src/yuantus/meta_engine/services/effectivity_service.py`
- Effectivity Router：`src/yuantus/meta_engine/web/effectivity_router.py`
- Substitute 写路径：`src/yuantus/meta_engine/services/substitute_service.py`
- 生命周期 guard：`src/yuantus/meta_engine/lifecycle/guard.py`
- 版本模型：`src/yuantus/meta_engine/version/models.py`
- 版本服务：`src/yuantus/meta_engine/version/service.py`
- 现有 release validation 基础件：`src/yuantus/meta_engine/services/release_validation.py`

## 4. 范围

### 4.1 自动编号 / 内部编码

目标不是“随便生成个号”，而是把编号生成收敛到一个可复用服务，并挂到标准创建路径。

最低要求：

- 新增 `NumberingService`，建议路径：`src/yuantus/meta_engine/services/numbering_service.py`。
- 由标准 Item 创建链路触发，优先挂在 `AddOperation.execute()` 或其明确委托路径，不要只在 seed/demo 路径生效。
- 默认策略是“仅当请求未提供编号时自动生成”，不能覆盖调用方显式传入的编号。
- 先定义一个主字段策略：
  - 生成后的 canonical 字段必须明确。
  - 当前主干里最稳定的消费面是 `properties.item_number`。
  - `number` / `internal_ref` 如需兼容，只能作为兼容镜像或读面兼容，不能把主语义做散。
  - 读路径的 fallback 顺序必须在 PR 内固化成一个模块级常量，例如 `ITEM_NUMBER_READ_KEYS = ("item_number", "number")`。
  - `product_service` / `query_service` / `search_service` / 其他直接消费 item 编号的服务必须共用这一常量，不允许各写各的 fallback 顺序。
- 编号规则必须可配置，配置范围至少覆盖 ItemType；若当前代码现实允许，也可细化到 Category/属性值，但不要把首版做成复杂规则引擎。
- 必须处理并发/重试下的撞号问题，不能靠“扫表取 max + 1”裸奔。
- `NumberingService` 必须暴露统一接口，内部按当前数据库方言选择最小实现：
  - Postgres：可用原生 sequence 或等价原子方案
  - SQLite：必须使用可重试的原子更新方案，不能假设 sequence 能力存在
  - 两种实现都必须被测试覆盖
- 必须说明 tenant/org 语义：
  - 若现有创建上下文已携带 tenant/org，就按现有上下文隔离。
  - 若当前链路拿不到 tenant/org，不要伪造；在 PR 说明里明确当前隔离边界。

设计约束：

- 优先复用现有元数据承载能力；如果当前模型放不下最小配置，再加最小 schema。
- 若加 schema，必须附 Alembic migration 与 migration coverage。
- 不要求首版实现“按年重置”“多段模板 DSL”“人工回拨序列”等高级能力。

### 4.2 仅最新已发布版本可被下游消费

目标是把“事后扫描 obsolete”前移到“写入时准入拦截”。

最低要求：

- 为 BOM child add、BOM substitute add、effectivity create 这三类写路径增加统一 guard。
- guard 必须是服务层复用 helper，不允许在多个 router/handler 里散落字符串判断。
- guard helper 首版签名固定为 `assert_latest_released(session, target_id, *, context)`，其中 `context` 至少覆盖 `bom_child`、`substitute`、`effectivity`。
- guard 失败时统一抛自定义异常，例如 `NotLatestReleasedError(reason, target_id)`，由 router 层映射为 `409`。
- 判定口径必须同时考虑：
  - Item 是否 current
  - 对应 current version 是否 released
  - 非 current、非 released、obsolete/superseded 这些下游不允许消费的情况
- 返回冲突时给明确错误：
  - 推荐 `409 Conflict`
  - detail 里要能说明是“not latest released”还是“current version not released”之类的原因
- Router 只负责把 service 错误映射为稳定 HTTP，不要把业务逻辑塞进 router。

首版至少覆盖这些写入口：

- `BOMService.add_child()`
- `SubstituteService.add_substitute()`
- `EffectivityService.create_effectivity()` 或其上层稳定服务入口

与 `release_validation.py` 的关系必须明确分离：

- `release_validation.py` 仍是 release-time 批量规则集
- 本次 guard 是 write-time 单点拦截
- 二者不合并、不互相 import 成一团
- 命名与报错风格可对齐，但实现应独立，建议单独放在 `services/latest_released_guard.py` 或等价位置

启用策略：

- guard 默认启用
- 但必须预留最小回滚开关，支持通过现有 tenant/org scoped config 机制或 settings fallback 临时关闭
- 不要发明新的配置框架；优先复用当前已有的 scoped plugin config / settings 模式
- 回滚开关是灰度保护，不是功能非目标

如果你发现还有同语义旁路入口：

- 可以补 guard
- 但必须把变更面控制在同一 PR 可审范围内
- 不要借机做全仓大搜大改

## 5. 非目标

这次不要做：

- `Suspended` 生命周期态
- 采购/销售/MBOM 全链路 released-only 扩散
- scheduler / outbox
- router 巨石拆分
- workbench/UI 设计改版
- pack-and-go / CAD / P1/P2 相关逻辑调整
- 新的大型 numbering DSL 或审批模板系统

## 6. 验收标准

### 6.1 自动编号

- 未提供编号的 Item 创建成功后，能稳定得到自动编号。
- 已提供 `item_number` 的请求不会被覆盖。
- 相同规则连续创建得到单调递增且无重复编号。
- 失败重试不会造成 silent duplicate。
- 编号生成逻辑可被单测直接调用，不依赖 HTTP。
- 至少有一个服务/路由级测试证明 AML add 主链已接入自动编号。

### 6.2 最新已发布版本约束

- 对非 current item、current version 未 released、或被判定为非“最新已发布”的目标，BOM child add 被拦截。
- 同样约束适用于 substitute add。
- 同样约束适用于 effectivity create。
- 对合法的 latest released target，不影响现有成功路径。
- 错误码、错误文案、事务边界稳定，失败不残留半成品关系或 effectivity 记录。

### 6.3 边界与兼容

- 不回归现有 P1/P2 主链测试。
- 不破坏当前显式编号调用方。
- 不破坏现有 `item_number` 读取面。
- 若新增配置或 schema，文档、seed、migration coverage 一并补齐。

## 7. 需要的测试

至少补这些测试，不够就继续加：

- `NumberingService` 单测：
  - missing number 自动生成
  - explicit number 不覆盖
  - 连续生成递增
  - 撞号/重试处理
  - Postgres / SQLite 方言分叉策略
  - 配置缺失/非法配置报错
- Item 创建主链测试：
  - `AMLEngine` / `AddOperation` 路径接入自动编号
  - 读路径 fallback 常量被统一复用
- BOM guard 测试：
  - latest released 允许
  - non-current 拒绝
  - current but unreleased 拒绝
- Substitute guard 测试：
  - 同上
- Effectivity guard 测试：
  - 同上
- Router/HTTP 测试：
  - 409 映射正确
  - 权限语义未退化
- 灰度/回滚测试：
  - guard enabled 默认生效
  - tenant/org scoped rollback 或 settings fallback 关闭后，旧行为可暂时恢复
- 如果有 migration：
  - migration coverage / contract test 通过
- 如果新增开发文档：
  - delivery doc index completeness / sorting contracts 通过

## 8. 推荐实现顺序

1. 先做一个最小可用 `NumberingService` 与测试。
2. 接入 `AddOperation` 主链，确保显式编号不被覆盖。
3. 抽一个统一的 latest-released guard helper。
4. 接入 `BOMService.add_child()`。
5. 接入 `SubstituteService.add_substitute()`。
6. 接入 `EffectivityService.create_effectivity()`。
7. 跑 focused tests，再跑必要回归。
8. 写开发及验证 MD。

## 9. PR 交付要求

Claude 提交 PR 时必须包含：

- 变更摘要
- 为什么选择当前编号配置承载方式
- 为什么选择当前 latest-released 判定口径
- 新增/修改的测试清单
- 已跑命令与结果
- 已知边界

PR 范围控制要求：

- 优先单 PR 完成，但仅限这个 bounded increment。
- 不顺手修 unrelated failing tests。
- 不顺手整理风格、命名、无关 router。
- 如果发现需要第二步 UI/配置补面，单独列 follow-up，不塞进本 PR。

## 10. Codex 审阅清单

我会按下面清单审 Claude 的 PR：

1. 自动编号是否真的挂在标准创建主链，而不是 seed/demo/单一路由。
2. 是否把 canonical 字段定义清楚，避免 `item_number` / `number` / `internal_ref` 三套语义继续发散。
3. 是否存在并发撞号窗口。
4. latest-released guard 是否复用 helper，而不是在多个入口硬编码。
5. 是否把“current”和“released”两个维度混为一谈。
6. 失败是否回滚干净，有无半成品 BOM line / substitute / effectivity。
7. HTTP 映射是否稳定，409/400/403/404 没有串。
8. migration 是否最小且可回放。
9. 是否有 scope creep。
10. 开发及验证 MD 是否能支撑 merge。

## 11. 交付文档要求

Claude 完成后至少补一份：

- `docs/DEV_AND_VERIFICATION_*.md`

文档中必须包含：

- 目标
- 设计选择
- 改动范围
- 测试命令
- 测试结果
- 已知边界

若新增了新的开发任务/交付文档，记得同步 `docs/DELIVERY_DOC_INDEX.md`。

## 12. 建议给 Claude Code CLI 的启动提示词

可直接把下面这段发给 Claude：

```text
请按 docs/DEVELOPMENT_CLAUDE_TASK_AUTO_NUMBERING_LATEST_RELEASE_GUARD_20260420.md 执行。

约束：
1. 只做自动编号 + latest released guard。
2. 以当前主干代码现实为准，不以历史 gap 文档逐字为准。
3. 不做 Suspended、scheduler、outbox、router 拆分、UI 大改。
4. 先实现、补测试、再补开发及验证 MD。
5. PR 必须可被 Codex findings-first 审阅。

完成后给出：
- 改动摘要
- 测试结果
- 开发及验证 MD 路径
- 需要 Codex 重点审的风险点
```
