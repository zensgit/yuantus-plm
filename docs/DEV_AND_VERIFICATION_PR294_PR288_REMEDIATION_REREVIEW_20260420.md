# DEV_AND_VERIFICATION_PR294_PR288_REMEDIATION_REREVIEW_20260420

## 1. 目标

对两条并行增量的 remediation 做一次独立复审：

- **PR #294（Line A）** 自动编号 + latest-released guard 的独立审阅 remediation
- **PR #288（Line B）** CAD backend profile 的独立审阅 remediation + 142 shared-dev smoke

复审约束（用户在驱动时明确）：

- 不修改任何核心代码逻辑
- 不登记任何新 MD 到交付索引（由 Codex / 用户决定）
- 仅做代码证据核对 + 测试重跑 + merge 建议

## 2. 复审来源文档

### Line A（PR #294）

- `/Users/chouhua/Downloads/Github/Yuantus-worktrees/next-main-20260420/docs/DEV_AND_VERIFICATION_AUTO_NUMBERING_LATEST_RELEASED_GUARD_REVIEW_REMEDIATION_20260420.md`

### Line B（PR #288）

- `/Users/chouhua/Downloads/Github/Yuantus-worktrees/cad-backend-profile-independent-review-remediation-20260420/docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_REMEDIATION_20260420.md`
- `/Users/chouhua/Downloads/Github/Yuantus-worktrees/cad-backend-profile-independent-review-remediation-20260420/docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md`
- `/Users/chouhua/Downloads/Github/Yuantus-worktrees/cad-backend-profile-independent-review-remediation-20260420/tmp/cad-backend-profile-142-sanitized-20260420-174219/summary_report.json`

### 原始独立审阅（Line B）

- `/Users/chouhua/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_20260420.md`

## 3. 判定摘要

| PR | 修复项 | 判定 |
|---|---|---|
| #294 Line A | F1 `/aml/apply` 旁路 | ✅ 真修 |
| #294 Line A | F2 numbering 历史 floor bootstrap | ✅ 真修 |
| #294 Line A | F4d update item_number/number 双写 | ✅ 真修 |
| #288 Line B | F1 shell verifier trap restore | ✅ 真修（实现比原建议更严谨） |
| #288 Line B | F2 PUT 403 回归测试 | ✅ 真修 |
| #288 Line B | F4 worker tenant fail-loud | ✅ 真修（实现比原建议更好） |
| #288 Line B | 142 shared-dev smoke | 🟡 Blocked not failed（远端未部署新路由） |

**总裁定**：两条 PR 的 remediation 全部为真修，非文案/测试 patch。建议按 Codex 规划推进合并。

## 4. Line A 详细证据

### 4.1 F1 · `/aml/apply` 旁路堵上

**原始声明**：
> `AddOperation` 增加 relationship write-time guard，覆盖 `Part BOM` / `Manufacturing BOM` / `Part BOM Substitute`，guard 位置放在 `on_before_add` 之后，按最终 `related_id` 判定，避免 method hook 改 target 后漏检

**代码证据**：
`src/yuantus/meta_engine/operations/add_op.py`

- L11：`from yuantus.meta_engine.services.latest_released_guard import assert_latest_released`
- L18–22：`RELATIONSHIP_GUARD_CONTEXTS` 映射三种关系 ItemType 到对应 guard context
- L24–36：`_assert_relationship_target_latest_released` helper，校验 `new_item.related_id`
- L79：guard 调用位置在步骤 6，**位于步骤 5（method hook `on_before_add`）之后**

`src/yuantus/meta_engine/web/router.py`

- L8：`from ..services.latest_released_guard import NotLatestReleasedError`
- L48–50：`except NotLatestReleasedError` → 映射 `409 Conflict` + `exc.to_detail()`

**复审观察**：
关键架构亮点是**把 guard 下沉到 `AddOperation` 而不是 `BOMService` / `SubstituteService`**。这意味着所有经由 `/aml/apply` 的 nested relationship add、bulk 创建、导入路径都天然被覆盖，不可能有「另一条路径漏校」的隐患。

### 4.2 F2 · numbering 历史 floor bootstrap

**原始声明**：
> sequence 空表时不再盲目从 `start=1` 起跳；先扫同 ItemType 下已有 `properties.item_number` / `properties.number`；insert/upsert 与 generic update 分支都尊重 floor；测试环境若没有 `meta_items` 表，则安全降级为空历史

**代码证据**：
`src/yuantus/meta_engine/services/numbering_service.py`

- L234–251 `_floor_allocated_value`：
  - L236–243：`try ... except OperationalError: return existing_max + 1` — 表不存在时静默降级
  - L244–250：扫同 ItemType 所有 Item，用共享 `get_item_number()` 解析编号，取历史最大
  - L251：返回 `existing_max + 1`
- L127–130（Postgres）：`func.greatest(last_value + 1, floor_value)`
- L140–143（SQLite）：`func.max(last_value + 1, floor_value)`
- L156 / L181：upsert 与 generic 两条分支都调用 `_floor_allocated_value`

**复审观察**：
- ✅ 使用共享的 `get_item_number()` helper（来自 `services/item_number_keys.py`），这个 helper 内部用 `ITEM_NUMBER_READ_KEYS = ("item_number", "number")` 常量——与 F4d 的读路径常量完全同源
- ✅ 两方言（Postgres / SQLite）通过 `GREATEST` / `MAX` 函数在同一 statement 内原子地取 `max(counter+1, floor)`，不存在 read-then-write 的 race

**性能观察（非阻塞）**：
`_floor_allocated_value` 每次分配都做**全表扫描 + Python 端逐行解析**。对大历史库（> 10 万 Item）会有明显延迟。建议登记为 follow-up：下推到 DB 层，`SELECT MAX(CAST(substring(...) AS INTEGER))` 或预先加索引列。

### 4.3 F4d · update item_number / number 双写

**原始声明**：
> update 时优先取本次请求里的 `item_number` / `number`，再通过 shared helper 同步回两个 alias；不再让旧数据里残留的 `item_number` 把本次 legacy `number` 更新覆盖回旧值

**代码证据**：
`src/yuantus/meta_engine/operations/update_op.py`

- L9–12：import `ensure_item_number_aliases`、`get_item_number`
- L44–47：
  ```python
  merged = dict(item.properties or {})
  merged.update(aml.properties or {})
  alias_value = get_item_number(aml.properties or {}) or get_item_number(merged)
  merged = ensure_item_number_aliases(merged, alias_value)
  ```

`src/yuantus/meta_engine/services/item_number_keys.py`

- L7：`ITEM_NUMBER_READ_KEYS = ("item_number", "number")`
- L10–21 `get_item_number`：按 `ITEM_NUMBER_READ_KEYS` 顺序拾取非空字符串
- L24–33 `ensure_item_number_aliases`：写回两键

**复审观察**：
- ✅ 关键行是 L46 的 `get_item_number(aml.properties) or get_item_number(merged)` —— **请求优先，再 fallback 到 merged 视图**。这直接修掉了「旧 `item_number` 覆盖本次 `number` 更新」的路径。
- ✅ 读路径 fallback 常量 `ITEM_NUMBER_READ_KEYS` 在 `item_number_keys.py:7` 定义，被 update_op + numbering_service 共用——符合 `DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` §4.1 对「读路径 fallback 顺序必须固化成模块级常量、多服务共用」的要求。

### 4.4 Line A 测试重跑

本复审在 `next-main-20260420` worktree 下用 `/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python` 重跑了 remediation MD 声明的 focused suite：

```bash
python -m pytest -q \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/operations/tests/test_update_op.py \
  src/yuantus/meta_engine/tests/test_latest_released_guard_router.py \
  src/yuantus/meta_engine/tests/test_latest_released_write_paths.py \
  src/yuantus/meta_engine/tests/test_numbering_service.py
```

**结果**：27 passed in 0.74s

3 份 doc-index contract tests：

```bash
python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

**结果**：3 passed in 0.02s

## 5. Line B 详细证据

### 5.1 F1 · shell verifier trap restore

**原始声明**：
> 新增 restore 状态跟踪 + `trap restore_if_dirty EXIT`，`restore_override_applied=1` 前移到第一次 PUT 之前，覆盖 PUT 已在服务端部分生效但客户端失败的窗口；trap handler 内 `set +e`

**代码证据**：
`scripts/verify_cad_backend_profile_scope.sh`

- L12：`restore_override_applied=0` （全局初始化）
- L22：`restore_override_applied=0` （clear_restore_state helper 重置）
- L377–402：`restore_if_dirty()` 函数
- L379：`trap - EXIT` 在 handler 内清 trap，避免再次触发
- L385：**`set +e`**——trap 内禁用 errexit，防止二次 restore 失败掩盖原始退出码
- L404：`trap restore_if_dirty EXIT`
- L437：`restore_override_applied=0`（读 initial state 阶段）
- L440：`restore_override_applied=1` **在第一次 PUT 之前前移**

**复审观察**：
比我原始建议的「加 `trap EXIT` + guard flags」**实现更严谨**：
- `set +e` 的细节我没提到；没有它会导致 trap handler 自身因 set -e 中止
- flag 前移到 PUT 之前，覆盖「服务端已生效但客户端收到超时 / 5xx」的窗口——这是比简单的「PUT 返回 200 后置 flag」更严格的语义

Codex 还额外补了 `test_ci_contracts_cad_backend_profile_scope_verifier.py` 里的**行为测试**：用 mock HTTP server 强制故意失败，断言脚本退出前确实发出了 restore 请求，且服务端状态回到初始 profile。这不是 grep `trap` 就能代替的，是真的验证了 F1。

### 5.2 F2 · PUT 403 回归测试

**代码证据**：
`src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py:98-102`

```python
def test_put_backend_profile_requires_admin() -> None:
    client, _ = _client(SimpleNamespace(id=2, roles=["viewer"]))
    response = client.put(
        "/api/v1/cad/backend-profile",
        json={"profile": "hybrid-auto", "scope": "tenant"},
    )
    assert response.status_code == 403
```

**复审观察**：
与 DELETE 的 403 测试（L98-101）对齐，补齐了我原始审阅中指出的 regression 缺口。3 行测试、零架构改动。

### 5.3 F4 · worker profile fail-loud

**原始声明**：
> `_cad_backend_profile_resolution()` 现在要求 `ctx.tenant_id` 存在，缺失时抛 `JobFatalError(...)`；worker/job 漏传 tenant_id 时以 non-retryable fatal error 失败

**代码证据**：
`src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`

- L40：`from yuantus.meta_engine.services.job_errors import JobFatalError`
- L183–188：
  ```python
  ctx = get_request_context()
  if ctx.tenant_id is None:
      raise JobFatalError(
          "CAD backend profile resolution requires tenant context; "
          "check job payload includes tenant_id/org_id"
      )
  ```

**复审观察**：
这里 Codex **升级了我的原建议**：

- 我原建议是 `raise RuntimeError(...)`
- Codex 改成 `raise JobFatalError(...)`——non-retryable fatal error，避免 worker 把配置错误当作通用异常**反复重试**

这是更好的选择：
1. 配置错误重试永远不会成功，retry 只消耗 worker 容量
2. `JobFatalError` 语义与现有 job error 协议对齐（详见 `services/job_errors.py`）

### 5.4 Line B 测试重跑

在 `cad-backend-profile-independent-review-remediation-20260420` worktree 下：

```bash
python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

**结果**：32 passed in 2.26s

## 6. 142 Shared-dev Smoke · 证据查验

读取 `summary_report.json`：

```json
{
  "target": "shared-dev-142",
  "base_url": "http://142.171.239.56:7910",
  "health_status": 200,
  "login_status": 200,
  "backend_profile": {
    "noauth_status": 401,
    "admin_status": 404,
    "body": {"detail": "Not Found"},
    "present_in_openapi": false
  },
  "capabilities": {
    "status": 200,
    "present_in_openapi": true,
    "cad_connector_keys": [
      "base_url", "configured", "degraded_reason",
      "enabled", "mode", "status"
    ],
    "has_profile_block": false
  }
}
```

**判定**：
- `/api/v1/cad/backend-profile` 在远端 OpenAPI 中 **不存在**
- `/api/v1/cad/capabilities` 的 `integrations.cad_connector` 字段 **不含 `profile` 块**——仍是旧 shape

说明远端 142 服务**尚未部署**含 CAD backend profile 请求面的版本。
MD 的定性「smoke blocked because remote not deployed, not smoke failed」**与数据一致**。
本地 clean worktree 的 **32 passed** 成为 Line B 的主验证证据。

**后续建议**：等 142 升级到含 `/api/v1/cad/backend-profile` 的版本后重跑同一 verifier，不是本次 merge 的前置。

## 7. 小发现（非阻塞，仅登记）

### 7.1 Line A · numbering 历史 floor 的 O(N) 扫表

`_floor_allocated_value` 每次自动编号分配时都走全表扫 + Python 端解析。
对大型历史库（10 万 Item 量级）会有延迟累计。

**建议**（follow-up PR）：

- 改为 `SELECT MAX(CAST(substring(item_number, length(prefix)+1) AS INTEGER))` 下推到 DB
- 或 materialize 一个独立编号列 + 索引

**不阻塞本次 merge**——小部署规模下不可观察，大部署规模下是可观察但可容忍的性能问题。

### 7.2 Line A + Line B · `require_admin` 又被复制一次

与 `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` §二.2 登记的「`security/rbac/permissions.py` + `meta_engine/permission/models.py` 双份声明」是同一条技术债。
目前 `require_admin` 在 4 个 router 中完全复制：

- `cad_router.py:77-81`
- `search_router.py:14-18`
- `schema_router.py:18-22`
- `permission_router.py:17-21`

**建议**（独立 follow-up PR）：

- 统一到 `src/yuantus/security/rbac/dependencies.py::require_admin`
- 四个 router 改为从统一位置 import

**不阻塞本次 merge**——是仓库级已知债务，与 PR #288 / #294 的 scope 无关。

## 8. Merge 建议

| 项 | 判定 | 说明 |
|---|---|---|
| PR #294 Line A | 🟢 可合 | 3 个 blocker 全部真修，27 focused + 3 contract 全绿 |
| PR #288 Line B | 🟢 可合 | 3 个 blocker 全部真修，32 focused 全绿，142 smoke blocked 证据充分 |
| 合并顺序 | 互不依赖 | CI 先绿哪条先合 |
| 142 smoke 回归 | follow-up | 远端升级后再重跑，不是本次 merge 前置 |
| 7.1 numbering 性能优化 | follow-up | 独立 PR |
| 7.2 `require_admin` 去重 | follow-up | 独立 PR |

## 9. 本复审未做的事

- 未修改任何代码（遵守用户约束「不要再改 #294 的核心代码逻辑」）
- 未登记任何新文档到 `DELIVERY_DOC_INDEX.md`（由 Codex 或用户决定）
- 未跑远端 142 smoke（远端未部署新路由，跑也只会复现 404）
- 未做 Line A 与 Line B 的任何 merge 操作

## 10. Reviewer

本复审由本会话的 Claude 助手以 findings-first 方式完成。
复审视角：独立、不偏向 Codex 自评或原始 Claude 实现。
所有判定基于代码直接阅读 + 测试重跑 + JSON 证据 + MD 交叉对照，不依赖任何一方的声明。
