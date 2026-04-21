# DEV / Verification - PR288 Targeted Code Review

日期：2026-04-20

## 目标

对 PR `#288` 做窄范围代码复审，只覆盖此前要求的 4 个点：

1. F1 `verify_cad_backend_profile_scope.sh` 的 failure-path restore
2. F2 `PUT /api/v1/cad/backend-profile` 的 `403` 权限回归
3. F4 worker 侧 `tenant_id/org_id` 缺失时的 fail-loud 行为
4. shared-dev `142` smoke 的证据链是否成立

本轮不是全量重审，也不覆盖 CAD profile 之外的其它改动。

## 审阅对象

- PR：`#288`
- 标题：`Harden CAD backend profile review remediation`
- 审阅 head：`428d564716a8757d956e50ea34532a8ee5dbf0d1`
- GitHub 状态：`closed`
- Merge 状态：`merged`

## 归档说明

这份文档最初在 PR `#288` 的 clean worktree 中产出，随后后移归档到主仓库 `docs/`，用于保留 merge 后的 targeted re-review 结论。

本轮原计划把窄范围审阅结论整理成一条可直接发到 PR 的 review；执行时核到 PR `#288` 已经在 GitHub 上完成合并，因此没有再追加新的 PR review/comment，避免在已合并 PR 上重复噪声式收口。

## 结论

在上述窄范围内，本轮**未发现新的 merge-blocking 问题**。

四个目标点的结论如下：

| 项 | 结论 | 说明 |
| --- | --- | --- |
| F1 failure-path restore | 通过 | trap 恢复链路完整，且有 mid-run failure / PUT apply-then-fail 两条 contract test |
| F2 PUT 403 regression | 通过 | 路由真实依赖 `require_admin`，非 admin `PUT` / `DELETE` 都返回 `403` |
| F4 worker tenant fail-loud | 通过 | 缺 `tenant_id` 时在任务侧抛 `JobFatalError`，不会静默回落 |
| shared-dev 142 smoke | 证据成立 | 远端 smoke 当前是 `blocked`，原因是 `142` 尚未部署 backend-profile 路由，不是 PR 代码失效 |

## 代码证据

### F1 verifier failure-path restore

- [scripts/verify_cad_backend_profile_scope.sh](/Users/chouhua/Downloads/Github/Yuantus/scripts/verify_cad_backend_profile_scope.sh:5)
  - 顶部显式初始化 restore 状态，并提供 `clear_restore_state()`，避免脏状态跨轮残留。
- [scripts/verify_cad_backend_profile_scope.sh](/Users/chouhua/Downloads/Github/Yuantus/scripts/verify_cad_backend_profile_scope.sh:377)
  - `restore_if_dirty()` 读取原始退出码，先 `trap - EXIT`，再根据 `restore_override_applied` 决定是否执行恢复。
- [scripts/verify_cad_backend_profile_scope.sh](/Users/chouhua/Downloads/Github/Yuantus/scripts/verify_cad_backend_profile_scope.sh:430)
  - `verify_scope_flow()` 在发起 `PUT` 之前就写入 restore 元数据，并在 `PUT` 前把 `restore_override_applied=1` 打开，因此“服务端已应用但客户端收到失败”也能进入恢复。
- [src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py:209)
  - 覆盖 mid-run failure，断言非零退出时仍执行 restore。
- [src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py:249)
  - 覆盖 `PUT` “apply_then_fail” 路径，证明 trap 能回滚已经应用的 org override。

判定：F1 已修到位。

### F2 PUT 403 regression

- [src/yuantus/meta_engine/web/cad_router.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/cad_router.py:77)
  - `require_admin()` 只接受 `admin` 或 `superuser`。
- [src/yuantus/meta_engine/web/cad_router.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/cad_router.py:1032)
  - `PUT /backend-profile` 真实依赖 `Depends(require_admin)`。
- [src/yuantus/meta_engine/web/cad_router.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/cad_router.py:1058)
  - `DELETE /backend-profile` 同样依赖 `Depends(require_admin)`。
- [src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py:98)
  - 非 admin `PUT` 返回 `403`。
- [src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py:107)
  - 非 admin `DELETE` 返回 `403`。

判定：F2 已补齐到真实路由面，不是只测 helper。

### F4 worker tenant fail-loud

- [src/yuantus/meta_engine/services/job_worker.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/services/job_worker.py:142)
  - worker 仅在 payload 里存在 truthy `tenant_id` / `org_id` 时才写 request context。
- [src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py:180)
  - `_cad_backend_profile_resolution()` 发现 `ctx.tenant_id is None` 时直接抛 `JobFatalError`，不会静默回落到全局 profile。
- [src/yuantus/meta_engine/tests/test_cad_backend_profile.py](/Users/chouhua/Downloads/Github/Yuantus/src/yuantus/meta_engine/tests/test_cad_backend_profile.py:141)
  - 测试明确覆盖 `tenant_id=None` 路径，并断言报错信息包含 `requires tenant context`。

判定：F4 的“缺租户上下文要 fail loud”已成立。

## shared-dev 142 证据链

- [docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md](/Users/chouhua/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md:53)
  - `GET /api/v1/health` 为 `200`，`POST /api/v1/auth/login` 为 `200`，说明远端在线且凭证有效。
- [docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md](/Users/chouhua/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md:55)
  - 未鉴权 `GET /api/v1/cad/backend-profile` 为 `401`，admin 鉴权后为 `404`。
- [docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md](/Users/chouhua/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md:57)
  - `/openapi.json` 不含 `/api/v1/cad/backend-profile`，但含 `/api/v1/cad/capabilities`；且后者仍返回旧 shape。
- [docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md](/Users/chouhua/Downloads/Github/Yuantus/docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SHARED_DEV_142_SMOKE_20260420.md:83)
  - 文档结论与探针一致：这是远端环境版本落后导致的 smoke blocked，不是对 PR #288 的否定证据。

判定：142 证据链自洽，blocked 的归因成立。

## 验证

执行命令：

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：

- `32 passed in 2.36s`

## 剩余注意点

- 本轮没有重新做 `142` 部署；远端验证仍受当前 shared-dev 版本约束。
- `F4` 当前测试覆盖的是 `tenant_id=None`。如果后续真的担心“空白字符串 tenant_id”这类脏 payload，可再补一条输入卫生 hardening，但这不构成当前 PR 的 blocker。

## 建议

从本轮窄范围复审结论看，PR `#288` 在 F1 / F2 / F4 / `142` smoke 归因这四个点上可以通过。

由于该 PR 已合并，这份文档应作为 merge 后补充审阅归档使用；如果后续要继续扩大审阅范围，应另开一轮，不要把这份窄范围复审误当成全量 code review。
