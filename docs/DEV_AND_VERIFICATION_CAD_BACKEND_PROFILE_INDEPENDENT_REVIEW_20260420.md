# DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_20260420

## 1. 目标

对已落盘、未合并的 CAD backend profile 增量做一次**独立审阅**，专门扫 Codex 自评（四轮 DEV_AND_VERIFICATION MD）容易漏掉的盲区。

独立审阅的触发依据：第四轮 local smoke 过程中，Codex 在自评里未发现的 `USERNAME → LOGIN_USERNAME` shell 污染 bug 是真跑脚本才暴露的——这说明还可能有同类「自己写自己测」漏掉的洞。

## 2. 审阅范围

仅审下列 4 个独立视角才能抓到的点，不做全量复审：

1. `PUT/DELETE /api/v1/cad/backend-profile` 的 auth 一致性与测试覆盖
2. `meta_plugin_configs` 表被借用存 CAD profile 是否有语义污染
3. `scripts/verify_cad_backend_profile_scope.sh` 的 restore 在失败路径下是否仍成立
4. `cad_pipeline_tasks.py` 与 `cad_router.py` 两处 scoped resolver 的 tenant/org 上下文来源是否一致

## 3. 已审阅的上游交付

- `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SELECTION_20260420.md`
- `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_OVERRIDES_20260420.md`
- `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md`
- `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_LOCAL_SMOKE_20260420.md`

## 4. Findings

### F1 · shell verifier 没有 `trap`，失败会留脏 override（🔴 merge 前修）

**证据**：

- `scripts/verify_cad_backend_profile_scope.sh` L1-3 有 `set -euo pipefail`
- 全脚本 grep `trap` → **0 命中**
- restore 逻辑仅在 happy path 末尾 L398-408 执行

**影响链路**：

1. 脚本读 initial state（例如 `effective=local-baseline, source=legacy-mode`）
2. 脚本 PUT 测试 override（`effective=hybrid-auto`）
3. 任何 HTTP 校验失败、curl 超时、Ctrl-C 触发 `set -e` 中止
4. restore 不再执行
5. 租户 org 覆盖永久停留在 `hybrid-auto`，下一操作员不知道有残留

**与 MD 承诺不符**：
`DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md` 明确写「Restores the original org-scope state before exit」，该承诺仅在 happy path 为真。

**修复建议**：

- 在脚本头部加 `trap restore_if_dirty EXIT`
- 用两个 flag（`initial_captured`、`override_applied`）跟踪是否需要 restore
- EXIT handler 按 flag 决定是否发出 restore 请求
- 补一个 test：强制 mid-run 失败（例如 `curl ... && false`）并断言 scope 已清

---

### F2 · PUT 端点缺 403 分支测试（DELETE 有）（🟠 merge 前补）

**证据**：

- `tests/test_cad_backend_profile_router.py` L98-101
  `test_delete_backend_profile_requires_admin`：viewer DELETE → 403 ✅
- `tests/test_cad_backend_profile_router.py` L71-95
  `test_put_backend_profile_updates_tenant_scope`：仅断言 admin 的 200 成功路径
- **没有 `test_put_backend_profile_requires_admin`（viewer/engineer PUT → 403）**

**与代码现状对照**：

- `require_admin` 逻辑本身与 `search_router.py:14`、`schema_router.py:18`、`permission_router.py:17` 三处完全一致 ✅
- `cad_router.py:77-81` 的实现无问题 ✅

**风险**：缺测试意味着未来重构 require_admin 或换 dependency 写法时，PUT 的 403 分支没有 regression 防线。

**修复建议**：
补 3 行测试：

```python
def test_put_backend_profile_requires_admin() -> None:
    client, _ = _client(SimpleNamespace(id=2, roles=["engineer"]))
    response = client.put(
        "/api/v1/cad/backend-profile",
        json={"profile": "hybrid-auto", "scope": "tenant"},
    )
    assert response.status_code == 403
```

---

### F3 · `"cad-backend-profile"` plugin_id 是裸字符串，无保留机制（🟡 follow-up）

**已确认安全的面**：

- `PluginConfigService`（`services/plugin_config_service.py`）严格按 `plugin_id` 查询，不跨 plugin 枚举 ✅
- `/api/v1/plugins/{plugin_id}/config` 公共 API 有 `manager.get_plugin()` 404 守门 ✅
- 表层 `UniqueConstraint("plugin_id","tenant_id","org_id")` 防插入竞态 ✅
- `plugin_manager` 内部没有跨 plugin_id 的 config 枚举 / 清理操作 ✅

**剩余洞**：
`"cad-backend-profile"` 当前是**裸字符串**。若将来某个真 plugin 的 manifest 声明 `id: "cad-backend-profile"`，会在同一行键上撞库，UniqueConstraint 会阻断插入但双方都会以为对方的数据是自己的，诊断成本高。

**修复建议**（可进 follow-up PR）：

- 在 `cad_backend_profile_service.py` 里把 ID 定义为模块常量，例如 `_RESERVED_PLUGIN_ID = "cad-backend-profile"`
- 在 `plugin_manager/plugin_loader.py` 的 discover 阶段加一个「保留 plugin_id 列表」检查，遇到冲突 manifest 拒绝加载并打 warning
- 可联动 F5 的 `RESERVED_PLUGIN_IDS` 常量清单，集中管理

---

### F4 · 工人路径 profile 解析没有「context 必需」防御（🟠 merge 前修）

**上下文来源一致性（✅）**：

- 请求路径：`cad_router.py:1009-1014` 调 `get_request_context()` → `ctx.tenant_id, ctx.org_id`
- 任务路径：`cad_pipeline_tasks.py:182-186` 调 `get_request_context()` → `ctx.tenant_id, ctx.org_id`
- 工人 `job_worker.py:146-149` 会在任务执行前从 `payload["tenant_id"]` / `payload["org_id"]` 重新 set ContextVar
- 已观察到的 3 条 CAD 入队路径（`cad_router.py:1705`、`cad_router.py:2212`、`file_router.py:460`）均把 tenant/org 写进 payload ✅

**不存在「capabilities 与 job 报不同 profile」的直接 bug。**

**剩余洞**：
若未来某条新入队路径漏写 tenant_id / org_id 到 payload，worker 会以空 ContextVar 跑任务，`_cad_backend_profile_resolution()` 会**静默 fallback 到 env-level profile**。可能产生两种安静的错：

- 租户显式设 `local-baseline`，job 却走 env 默认的 `hybrid-auto`，隐式启用外部 connector
- 租户需要 `external-enterprise` fail-fast 保障，job 却走 `local-baseline` 静默降级

**修复建议**：
在 `cad_pipeline_tasks.py::_cad_backend_profile_resolution` 入口加一行防御，等价于：

```python
ctx = get_request_context()
if ctx.tenant_id is None:
    raise RuntimeError(
        "CAD backend profile resolution requires tenant context; "
        "check job payload includes tenant_id/org_id"
    )
```

配一个测试：构造一个 payload 漏写 tenant_id 的 job，worker 执行时期望抛 `RuntimeError`，而不是走 env fallback。

---

### F5（bonus）· `require_admin` 复制了 4 份（🟡 已知债务）

**证据**：

- `cad_router.py:77-81`
- `search_router.py:14-18`
- `schema_router.py:18-22`
- `permission_router.py:17-21`

四处逻辑一字不差：`"admin" not in roles and "superuser" not in roles → 403`。

**性质**：
这是本仓库原有的技术债（在 `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260420.md` §二.2 已登记）。**Line B 只是又新增了一处拷贝**，不是它引入的。

**修复建议**（follow-up）：

- 统一到 `src/yuantus/security/rbac/dependencies.py::require_admin`
- 四个 router 改为 `from yuantus.security.rbac.dependencies import require_admin`
- 独立 PR，和本次 merge 解耦

## 5. Merge 决定建议

| 级别 | 项 | 处理 |
|---|---|---|
| 🔴 merge 前修 | F1 shell trap | 在 Line B 最后加第 5 个 commit「hardening fixes after independent review」收掉 |
| 🟠 merge 前补 | F2 PUT 403 测试 | 同 commit，3 行测试 |
| 🟠 merge 前修 | F4 worker profile fail-loud | 同 commit，1 行 + 1 个测试 |
| 🟡 follow-up PR | F3 保留 plugin_id 机制 | 独立 PR，可与 F5 合并处理 |
| 🟡 follow-up PR | F5 require_admin 去重 | 独立 PR |

### Shared-dev 142 smoke 的建议顺序

如果决定在 merge 前过一次 shared-dev 142 smoke：

1. **先修 F1**：否则 smoke 脚本中途任何失败都会在 142 留下脏 override
2. **再修 F4**：避免 shared-dev 上一条漏 tenant_id 的入队路径静默走 env fallback
3. **修完后先本地重跑一次 smoke**（含 mid-run kill 断言），确认 trap + fail-loud 生效
4. **再上 shared-dev 142**

## 6. 不做的事

本独立审阅**不做**以下动作：

- 不改代码、不加测试、不跑 pytest
- 不写 remediation 代码（交给 Codex / Claude 按建议执行）
- 不对 F3 / F5 做范围扩张

## 7. 下一步

- 由 Codex 或 Claude 按 F1 / F2 / F4 三条建议产出 hardening commit
- 产出后可补一份 `DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_REMEDIATION_20260420.md`，沿用 `DEV_AND_VERIFICATION_ECO_PARALLEL_FLOW_HOOK_REVIEW_REMEDIATION_20260418.md` 的范式
- F3 / F5 登记为独立 follow-up PR，不卡本次 merge

## 8. 交付索引同步

本 MD 落盘后请同步更新：

- `docs/DELIVERY_DOC_INDEX.md`
- 若有 `test_dev_and_verification_doc_index_completeness.py` / `test_dev_and_verification_doc_index_sorting_contracts.py` / `test_delivery_doc_index_references.py` 相关 contract，确认这三项仍 passed

## 9. 已知边界

- 审阅只基于静态代码阅读与上游 MD 内容，**未实际执行测试或 smoke 脚本**
- `ctx.tenant_id is None` 的 fail-loud 修复在实施时需要确认是否会影响 legacy 入队路径（若有路径故意不带 tenant，属于旧行为，需要先清理）
- F1 的 `trap EXIT` 修复需要注意：若脚本自身靠 `set -e` 中断后 trap handler 再失败一次，需要 handler 内 `set +e`，否则二次失败会掩盖首次错误码

## 10. Reviewer

独立审阅由本会话的 Claude 助手完成，非 Codex 自评。审阅视角 findings-first，不假设 Codex 已经想到；如发现与 Codex 主张冲突处，按代码实际行为陈述。
