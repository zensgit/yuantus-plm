# DEV & Verification: CAD Backend Profile Independent Review Remediation (2026-04-20)

## 1. 目标

落实独立审阅文档 `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_INDEPENDENT_REVIEW_20260420.md` 中 3 个 merge 前项：

- F1: verifier failure-path restore
- F2: `PUT /api/v1/cad/backend-profile` 的 `403` 测试缺口
- F4: worker 路径 tenant/org context 缺失时 fail-loud

本轮不处理 follow-up 项：

- F3: reserved plugin_id 机制
- F5: `require_admin` 去重

## 2. 代码改动

### F1 · shell verifier failure-path restore

文件：

- `scripts/verify_cad_backend_profile_scope.sh`

改动：

- 新增 restore 状态跟踪变量与 `clear_restore_state()`
- 新增 `trap restore_if_dirty EXIT`
- 将 restore 逻辑从仅 happy path 扩展为 exit-path 保底执行
- `request_json()` / `assert_json_equals()` 从 `exit 1` 改为 `return 1`
  - 这样主流程仍受 `set -e` 保护
  - 但 trap 内可以在 `set +e` 下安全复用
- `--help` 文案改为明确说明：失败/中断时也会尝试 restore

结果：

- mid-run 失败不再把 scoped override 留脏在目标 tenant/org 上

### F2 · PUT 403 测试补齐

文件：

- `src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py`

改动：

- 新增 `test_put_backend_profile_requires_admin()`

结果：

- `PUT /api/v1/cad/backend-profile` 现在和 `DELETE` 一样有显式 `403` regression 防线

### F4 · worker profile resolution fail-loud

文件：

- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/meta_engine/tests/test_cad_backend_profile.py`

改动：

- `_cad_backend_profile_resolution()` 现在要求 `ctx.tenant_id` 存在
- 缺失时抛：

```text
RuntimeError("CAD backend profile resolution requires tenant context; check job payload includes tenant_id/org_id")
```

- 补测试覆盖缺 tenant context 的失败路径
- 同时更新既有 task-level 测试，使其显式提供 request context

结果：

- worker/job 若漏传 `tenant_id`，不再静默 fallback 到 env-level profile

## 3. 测试补充

文件：

- `src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py`

新增一条真实行为测试：

- 启动最小 mock HTTP server
- 让 verifier 在 `GET /api/v1/cad/capabilities` 处故意失败
- 断言脚本退出前确实发出了 restore 请求
- 断言服务端状态已回到初始 profile

这条测试覆盖的是 F1 的核心风险，不只是 grep `trap`。

## 4. 验证

### 首轮

执行：

```bash
bash -n scripts/verify_cad_backend_profile_scope.sh

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py
```

结果：

- shell syntax: passed
- pytest: `13 passed`

### 收口轮

执行：

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：

- `31 passed`

## 5. 风险与边界

- 本轮只收 F1/F2/F4，不扩到 F3/F5。
- fail-loud 约束只落在 task/worker 路径，不改变请求读面行为。
- shell trap 采用 EXIT handler；handler 内显式 `set +e`，避免二次 restore 失败掩盖原始退出码。

## 6. 结论

独立审阅提出的 3 个 merge 前项已被针对性收口，且补上了对应 focused regression。
