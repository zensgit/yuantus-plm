# Claude 开发任务书：Lifecycle Suspended Guard（2026-04-21）

## 1. 目标

给 Claude Code CLI 一个**边界明确**的下一条 bounded increment，只做两件事：

1. 在 `LifecycleState` 上加语义标志 `is_suspended`，让系统能**程序化识别**一个状态是否是「已挂起」，而不是用 `state.name == "Suspended"` 字符串硬匹配。
2. 在 BOM / Substitute / Effectivity / AddOperation nested relationship 四类写路径上，增加统一的 **`assert_not_suspended`** guard，把 Suspended 的 Item 从下游消费里准入拦截。

完成后，Odoo `plm_suspended` 对标能力的主干 backend 部分落地；Yuantus 支持「工程件暂停使用、待复核」这一标准 PLM 场景。

## 2. 重要前提（来自当前主干现实，非历史 gap 文档）

- **Suspended 状态已经存在**——不要再创建。看 `src/yuantus/seeder/meta/lifecycles.py`：
  - 默认 lifecycle `lc_part_std` 已经有 `s_suspended` state（`version_lock=True, seq=35`）
  - 已经有 `released → suspended`（action `suspend`）与 `suspended → released`（action `resume`）transition
  - 也有 `suspended → obsolete`（action `obsolete`）
- **但代码里没有 `is_suspended` 标志**，guard 无法识别 Suspended 状态——这是本次要补的
- **不要**重写 `seed-identity` 或 lifecycle transition 逻辑，transition 部分已经可用
- 本任务是 bounded increment，**不**顺手推进：
  - `previous_state` / 自动 resume 语义
  - UI 层的 Suspended 指示器 / 按钮
  - 采购 / 销售 / 工单全链路扩散
  - scheduler / 自动到期 suspend
  - router 大拆分
- 保持现有权限模型、租户/org 语义、Line A 的 auto-numbering + latest-released guard 行为不回归

## 3. 当前代码入口（Claude 落地前必须实际读过，不凭记忆）

- LifecycleState 模型：`src/yuantus/meta_engine/lifecycle/models.py`（加 `is_suspended` 字段的位置）
- Lifecycle guard 工具函数：`src/yuantus/meta_engine/lifecycle/guard.py`（`get_lifecycle_state` 已有，guard 里可复用）
- Item 模型：`src/yuantus/meta_engine/models/item.py`（`state` / `current_state` 字段，本任务**不**改 schema）
- 默认 lifecycle 种子：`src/yuantus/seeder/meta/lifecycles.py`（`_ensure_state` 签名要加一个可选 `is_suspended` 参数）
- **参考实现模板**：`src/yuantus/meta_engine/services/latest_released_guard.py`（本次 guard 直接复用其 scoped config、exception、context 模式）
- Scoped 配置复用：`src/yuantus/meta_engine/services/plugin_config_service.py`（沿用 `meta_plugin_configs` 表）
- AML add 主链（nested relationship guard 接入）：`src/yuantus/meta_engine/operations/add_op.py`（`_assert_relationship_target_latest_released` 已建立了 pattern，本次加 `_assert_relationship_target_not_suspended`）
- BOM / Substitute / Effectivity 写路径：分别在 `services/bom_service.py::add_child`、`services/substitute_service.py::add_substitute`、`services/effectivity_service.py::create_effectivity`（均已经挂了 latest-released guard，pattern 可直接 mirror）
- Router 错误映射：`src/yuantus/meta_engine/web/router.py`、`src/yuantus/meta_engine/web/bom_router.py`、`src/yuantus/meta_engine/web/effectivity_router.py`（这些文件各自已有 `NotLatestReleasedError → 409`，本次必须同步加 `SuspendedStateError → 409`）
- CLI dev seeder：`src/yuantus/cli.py::seed_meta`（它也会创建 Part/Document 的 Suspended state；不要只改 `seeder/meta/lifecycles.py`）

## 4. 范围

### 4.1 Schema：`LifecycleState.is_suspended` 字段

最低要求：

- 在 `LifecycleState` 模型加 `is_suspended = Column(Boolean, default=False)` 字段
- 必须附 Alembic migration，遵循 repo 现有 idempotent inspector pattern；SQLite 用 `batch_alter_table`，PostgreSQL/其他方言用 `op.add_column`
- 列定义要求：`nullable=False` + `server_default=sa.false()`，确保旧数据升级后为 `False`
- downgrade 必须按方言安全 `drop_column`
- migration coverage contract test 必须通过
- 更新 `seeder/meta/lifecycles.py::_ensure_state` 签名：增加可选 `is_suspended=False` 参数；默认 lifecycle 的 `s_suspended` 必须 seed 时显式传 `is_suspended=True`
- 同步更新 `src/yuantus/cli.py::seed_meta` 内部 `ensure_state(...)` helper：增加 `is_suspended=False` 参数，并给 Part lifecycle 的 `Suspended` 显式 `is_suspended=True`
- 本 PR 不扩展 Document lifecycle 语义；如果发现现有 Document `Suspended` 也需要标记，写 follow-up，不塞进本 bounded increment
- **不**要做：把 `is_released` 改成枚举；把 `version_lock` 语义改了；给 `LifecycleState` 加别的 flags

### 4.2 Guard 服务：`SuspendedGuardService`

目标是建立「write-time 单点拦截，别让 Suspended 目标被消费」的能力，代码结构**严格 mirror** `latest_released_guard.py`。

最低要求：

- 新增 `src/yuantus/meta_engine/services/suspended_guard.py`
- 常量：
  - `SUSPENDED_GUARD_PLUGIN_ID = "suspended-guard"`
  - `SUSPENDED_GUARD_DISABLED_KEY = "disabled"`
- 异常：
  - `class SuspendedStateError(ValueError)`
  - 字段 `reason`、`target_id`
  - `_REASON_MESSAGES`：至少覆盖
    - `"target_suspended"` — "target item/version is in a suspended state"
    - `"current_version_suspended"` — "target item's current version resides on a suspended state"
  - `to_detail() -> dict` 结构与 `NotLatestReleasedError.to_detail()` 对齐，error code 不同（`SUSPENDED_STATE`）
- Service class `SuspendedGuardService`：
  - `is_enabled()` 逻辑完全同 `LatestReleasedGuardService.is_enabled()`，换 plugin_id 和 disabled key
  - **settings fallback**：支持 `SUSPENDED_GUARD_DISABLED` env 开关（沿用 `LATEST_RELEASED_GUARD_DISABLED` 同款 Setting，需在 `config/settings.py` 加字段，默认 `False`）
  - `assert_not_suspended(target_id, *, context: str) -> None`：
    - `context` 首版固定覆盖 `bom_child` / `substitute` / `effectivity`
    - `effectivity` context 要像 latest-released 一样，既能接 item_id 也能接 version_id
    - Item target：加载 `Item` + `ItemType`，通过 `get_lifecycle_state(session, item, item_type)` 拿到 state，读 `state.is_suspended`
    - Relationship target（仅 `effectivity`）：如果 `Item.related_id` 存在，先解引用到 related item，再按 Item target 规则检查；latest-released guard 已负责 relationship current/latest 分类，本 guard 不重复发明 latest 分类
    - Version target：加载 `ItemVersion` 后再加载其 parent `Item` + `ItemType`；优先检查 parent item lifecycle state，必要时用 `version.state` + parent item type lifecycle map 解析 `LifecycleState`
    - 如果是 `True`，抛 `SuspendedStateError(reason=..., target_id=...)`
- 模块 public function：
  - `def assert_not_suspended(session, target_id, *, context: str) -> None:` 薄封装
- 不实现：
  - UI / API 暴露
  - batch 检查
  - scheduled scan

### 4.3 Guard 接入点（4 条写路径）

每一条都 mirror 现有 `assert_latest_released` 的接入方式，**排在 `assert_latest_released` 之后**（latest-released 先判，Suspended 再判；两个 guard 都是 write-time 硬拦截，顺序影响错误分类但不影响最终阻断）。

1. **`BOMService.add_child`**（`services/bom_service.py`）
   - 在 `assert_latest_released(session, child_id, context="bom_child")` 之后追加 `assert_not_suspended(session, child_id, context="bom_child")`
2. **`SubstituteService.add_substitute`**（`services/substitute_service.py`）
   - 同上，`context="substitute"`
3. **`EffectivityService.create_effectivity`**（`services/effectivity_service.py`）
   - 对 item_id / version_id 两个 target 都要过 guard，`context="effectivity"`
4. **`AddOperation._assert_relationship_target_latest_released` 同级**（`operations/add_op.py`）
   - 复制一个 sibling `_assert_relationship_target_not_suspended`，共用同一个 `RELATIONSHIP_GUARD_CONTEXTS`
   - 在 `execute()` 里「method hook 之后、auto-numbering 之前」的位置，顺序调用两个 sibling helper

### 4.4 Router 错误映射

需要同步处理 3 个已有 latest-released 映射入口：

- `src/yuantus/meta_engine/web/router.py`：AML `/api/v1/aml/apply` nested relationship add
- `src/yuantus/meta_engine/web/bom_router.py`：BOM `add_child` + substitute `add_substitute`
- `src/yuantus/meta_engine/web/effectivity_router.py`：effectivity create

每个入口都新增：

- `except SuspendedStateError as exc: db.rollback(); raise HTTPException(409, exc.to_detail())`
- **放在** `NotLatestReleasedError` except 分支的紧邻位置
- 非目标：改 PLMException 层级；改其他 router

### 4.5 租户级灰度回滚

复用 Line A 同款 scoped config 模式，**不发明新机制**：

- 通过 `meta_plugin_configs` 表存 `plugin_id="suspended-guard"` 的 `{"disabled": true}` 配置
- 查找顺序：tenant+org → tenant-default → settings fallback
- 不需要新增 router 去管理这个开关（用 plugins API 或 CLI 直接写表即可，本 PR 不做）

### 4.6 非目标（不要做，列明）

- `previous_state` / 自动回退到挂起前的 state
- UI 上的「Suspended」徽标、侧栏标签、确认对话框
- 把 Suspended 从 `lc_part_std` 分离成独立 lifecycle
- 新增 `Suspended` 到其他 lifecycle（`lc_document_std` 等）——如果它们存在；**只**处理 `lc_part_std`
- 采购/销售/MBOM/Quality/工单等跨模块扩散
- `/api/v1/lifecycle/suspended-guard` 之类管理端点
- Breakages / helpdesk 联动
- scheduler

## 5. 验收标准

### 5.1 Schema + Seeder

- `LifecycleState.is_suspended` 字段存在，默认 `False`，Alembic migration 覆盖
- `lc_part_std` 的 `s_suspended` 在重新 seed 后，`is_suspended=True`
- CLI `seed-meta` 创建/更新的 Part lifecycle `Suspended` 在重新 seed 后，`is_suspended=True`
- 旧数据（pre-migration）升级后，所有既有 `LifecycleState` 行 `is_suspended=False`（由默认值保障）

### 5.2 Guard

- 对 Item 当前状态 `is_suspended=True` 的 target，BOM child add 被拦截（409）
- 同样约束适用于 substitute add、effectivity create、AML nested relationship add
- 对合法（非 Suspended）target，不影响现有成功路径
- guard 禁用开关：
  - 默认启用
  - `settings.SUSPENDED_GUARD_DISABLED=True` 时全局跳过
  - tenant-org / tenant-default scoped config `{"disabled": true}` 时对应租户跳过
- 失败时不残留半成品 BOM line / substitute / effectivity 记录，事务回滚干净
- `SubstituteService.ensure_substitute_item_type()` 的 bootstrap commit 不计入半成品 substitute row；验收关注业务 relationship 不残留
- `SuspendedStateError` 映射 409 稳定，不和 `NotLatestReleasedError` 的 409 分类混淆（不同 error code）

### 5.3 边界

- 不回归任何 Line A / Line B 测试
- 不破坏 PR #294 / #288 / #309 已合入的行为
- `LifecycleState` 模型、`get_lifecycle_state` 签名的既有调用点不受影响

## 6. 需要的测试（至少）

- `test_suspended_guard.py`：
  - `is_enabled` 默认 True、settings fallback 禁用、tenant-org scoped 禁用、tenant-default scoped 禁用四条路径
  - `assert_not_suspended` 在 item、version、relationship 三种形状下的正确判定
  - Suspended target 抛 `SuspendedStateError` 且 `to_detail()` shape 稳定
  - 非 Suspended target 不抛
- `test_suspended_write_paths.py`（与 `test_latest_released_write_paths.py` 并列）：
  - BOM `add_child` / Substitute `add_substitute` / Effectivity `create_effectivity` 对 Suspended target 的 409 拦截
  - 对合法 target 的成功路径
  - 事务回滚验证（失败后关系表没有半成品行）
- `test_add_op.py`（**扩展**，不替换）：
  - nested relationship add 针对 Suspended target 也会被 guard 拦截（和现有 latest-released 测试并列）
- Router/HTTP 测试：
  - AML `/aml/apply`、BOM `add_child`、BOM substitute、Effectivity create 四个 HTTP 入口里，`SuspendedStateError` 都被映射为 409，`reason` 字段存在
- Seeder 测试：
  - `seeder/meta/lifecycles.py` 的 `lc_part_std_suspended` 标为 `is_suspended=True`
  - `cli.py seed-meta` 的 Part lifecycle `Suspended` 标为 `is_suspended=True`
- Migration coverage test：
  - `LifecycleState.is_suspended` 字段在 migration 范围内
- 3 份 doc-index contract tests：必须全绿

## 7. 推荐实现顺序

1. 加 `LifecycleState.is_suspended` + Alembic migration，本地 `alembic upgrade head` 跑通
2. 更新两个 seeder 路径：`seeder/meta/lifecycles.py::_ensure_state` 和 `cli.py::seed_meta.ensure_state`，给 Part Suspended 显式 `is_suspended=True`
3. 写 `suspended_guard.py`（照搬 `latest_released_guard.py` 结构）+ 单测
4. 在 `add_op.py` 加 sibling helper + test 用例
5. 在 `bom_service.py` / `substitute_service.py` / `effectivity_service.py` 三处挂 guard + 扩 `test_*_write_paths.py`
6. 在 `web/router.py` / `web/bom_router.py` / `web/effectivity_router.py` 加 `SuspendedStateError → 409` 映射 + router HTTP test
7. 跑 focused regression + 3 份 contract test，再跑必要的 cross-module smoke
8. 写开发及验证 MD `docs/DEV_AND_VERIFICATION_LIFECYCLE_SUSPENDED_GUARD_20260421.md`
9. （可选）把当前工作区实际存在且尚未提交的 merge records 作为本 PR 首个 commit 一并带走；截至本任务书审阅时仅确认 `DEV_AND_VERIFICATION_PR309_NUMBERING_FLOOR_DB_PUSHDOWN_MERGE_20260421.md` 待收走，已在主干的 PR300/PR294 记录不要重复添加

## 8. PR 交付要求

Claude 提交 PR 时必须包含：

- 变更摘要
- 为什么 `is_suspended` 是 LifecycleState 的新字段而不是 Item 的 flag
- guard 判定口径（state 查找 fallback、scoped config 解析）
- 新增 / 修改的测试清单
- 已跑命令与结果
- 已知边界（尤其：只处理 `lc_part_std`；`lc_document_std` 等其他 lifecycle 不在本 PR 范围）

PR 范围控制：

- 优先单 PR，**仅限本 bounded increment**
- 不顺手修 unrelated failing tests
- 不顺手整理无关 router 风格
- 如发现需要 UI / 管理端点补面，单独列 follow-up，不塞进本 PR

## 9. Codex / 独立审阅清单

| # | 检查点 |
|---|---|
| 1 | `is_suspended` 是否真的作为 `LifecycleState` 的 schema 字段，而不是 `state.name == "Suspended"` 字符串硬匹配 |
| 2 | Alembic migration 最小且可回滚 |
| 3 | `SuspendedGuardService` 是否完全 mirror `LatestReleasedGuardService` 的 scoped config / exception / context 模式（否则就是新机制，不应该） |
| 4 | 4 条写路径都挂了 guard，且顺序 `latest_released` 在前、`not_suspended` 在后一致 |
| 5 | `SuspendedStateError` 与 `NotLatestReleasedError` 不共用 reason/error code，HTTP 映射 409 但 detail 可区分 |
| 6 | 事务是否干净回滚 |
| 7 | 默认启用 + 灰度回滚开关都有测试覆盖 |
| 8 | nested relationship add（AML `/aml/apply`）也被覆盖，不是只测 service-level 写路径 |
| 9 | 没有 scope creep（UI / scheduler / multi-lifecycle / 跨模块扩散） |
| 10 | 开发及验证 MD 能支撑 merge（目标、设计选择、改动范围、测试命令、测试结果、已知边界） |

## 10. 交付文档要求

Claude 完成后落一份：

- `docs/DEV_AND_VERIFICATION_LIFECYCLE_SUSPENDED_GUARD_20260421.md`

包含：

- 目标
- 设计选择（`is_suspended` 为何落在 state 层、guard 为何复用 scoped config）
- 改动范围
- 测试命令与结果
- 已知边界
- 对 Line A / Line B 回归的影响说明（预期零）

同步 `docs/DELIVERY_DOC_INDEX.md` 加 1 条索引项。

## 11. 给 Claude Code CLI 的启动提示词

```text
请按 docs/DEVELOPMENT_CLAUDE_TASK_LIFECYCLE_SUSPENDED_GUARD_20260421.md 执行。

约束：
1. 只做 LifecycleState.is_suspended + SuspendedGuardService + 4 条写路径 guard + router 409 映射。
2. 以当前主干代码现实为准，不以历史 gap 文档逐字为准。Suspended 状态已在 seeder 存在，不要重建。
3. 严格 mirror 现有 latest_released_guard.py 结构，scoped config 复用 meta_plugin_configs 表，不发明新机制。
4. 不做 Suspended previous_state / UI / scheduler / 跨模块扩散 / 管理端点。
5. 先 schema + seeder，再 guard service，再 4 条写路径挂接，再 router 映射，再测试，最后写开发及验证 MD。
6. PR 必须可被 findings-first 审阅，且不能把遗留 merge MD 的收尾和本 bounded increment 混为一谈——如需收走当前未提交的 PR #309 merge MD，收尾走 first commit 的 chore，再进 feature commit；不要重复添加已经在 main 的 PR300/PR294 记录。
7. Codex 已补充任务书审阅要求：router 映射必须覆盖 web/router.py、bom_router.py、effectivity_router.py；seeder 必须覆盖 seeder/meta/lifecycles.py 和 cli.py seed-meta；state resolution 必须使用 ItemType lifecycle_map fallback，不能只传 item_type=None。

完成后给出：
- 改动摘要
- 测试结果（focused + 3 份 contract test）
- 开发及验证 MD 路径
- 需要 Codex 重点审的风险点
```

## 12. 关键锚点（核对一次再动代码）

- `s_suspended` 在 `seeder/meta/lifecycles.py` **已存在**，Claude 只负责把 `is_suspended=True` flag 加上
- 参考模板 `latest_released_guard.py` 在 `services/` 下已落盘，签名稳定
- 租户级 scoped config 的 plugin_id 命名**必须**不同于 latest-released（用 `"suspended-guard"`）
- 错误码、error detail shape 不与 `NotLatestReleasedError` 共用
