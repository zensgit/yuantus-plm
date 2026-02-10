# Release Orchestration Runbook

目的：用一套 **admin-only** API，把同一 `item_id` 相关的资源（Routing / MBOM / Baseline）按固定顺序做 **plan + execute**，并返回结构化诊断与可选回滚结果，形成“一键发布闭环”。

相关交付说明（设计/验证证据）：`docs/DEV_AND_VERIFICATION_RELEASE_ORCHESTRATION_20260208.md`。

## 0) 前置条件

- API 已运行：`http://127.0.0.1:7910`
- 已获得 admin/superuser 的 `$TOKEN`
- 已知 `item_id`（要发布的目标 Item）
- 多租户下请带上租户/组织头：
  - `x-tenant-id: tenant-1`
  - `x-org-id: org-1`

## 1) Plan（只读预览，不改状态）

接口：

- `GET /api/v1/release-orchestration/items/{item_id}/plan`

示例：

```bash
BASE_URL=http://127.0.0.1:7910

curl -s "$BASE_URL/api/v1/release-orchestration/items/<item_id>/plan?ruleset_id=default&routing_limit=20&mbom_limit=20&baseline_limit=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' | jq .
```

你会得到：

- `readiness`：Release Readiness 的汇总（包含资源列表与 diagnostics）
- `steps[]`：按执行顺序排好的动作清单（routing -> mbom -> baseline）
  - `action` 可能值：
    - `release`：满足条件可执行
    - `skip_already_released`：已 released，执行时会跳过
    - `skip_errors`：diagnostics 有 errors，执行时会跳过
    - `requires_esign`：baseline 可发布但电子签名清单不完整（执行时会被阻止）

## 2) Execute（可 dry-run / 可选回滚）

接口：

- `POST /api/v1/release-orchestration/items/{item_id}/execute`

请求体字段（常用）：

- `ruleset_id`：规则集（默认 `default`）
- `include_routings`：是否包含 routing release（默认 `true`）
- `include_mboms`：是否包含 mbom release（默认 `true`）
- `include_baselines`：是否包含 baseline release（默认 `false`）
- `routing_limit/mbom_limit/baseline_limit`：每类资源最多处理多少条（默认 20，上限 200）
- `dry_run`：只生成 results，不改状态（默认 `false`）
- `continue_on_error`：遇到失败是否继续（默认 `false`）
- `rollback_on_failure`：失败时把本次已 release 的资源 best-effort reopen 回 draft（默认 `false`）
  - 约束：`rollback_on_failure=true` 要求 `continue_on_error=false`
- `baseline_force`：baseline release 在 diagnostics 有 errors 时是否强制执行（默认 `false`）
  - 注意：电子签名清单不完整时仍会阻止 baseline release

### 2.1 Dry-run（推荐先跑一次）

```bash
BASE_URL=http://127.0.0.1:7910

curl -s -X POST "$BASE_URL/api/v1/release-orchestration/items/<item_id>/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{
    "ruleset_id": "default",
    "include_routings": true,
    "include_mboms": true,
    "include_baselines": false,
    "dry_run": true
  }' | jq .
```

预期：

- `dry_run=true`
- `results[].status` 多为 `planned`/`skipped_*`
- 不会发生任何状态变更

### 2.2 正式执行（失败即停止）

```bash
curl -s -X POST "$BASE_URL/api/v1/release-orchestration/items/<item_id>/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{
    "ruleset_id": "default",
    "include_routings": true,
    "include_mboms": true,
    "include_baselines": false,
    "continue_on_error": false,
    "rollback_on_failure": false,
    "dry_run": false
  }' | jq .
```

### 2.3 失败自动回滚（best-effort）

用于“部分资源已 release，但后续失败”的场景：

```bash
curl -s -X POST "$BASE_URL/api/v1/release-orchestration/items/<item_id>/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{
    "ruleset_id": "default",
    "include_routings": true,
    "include_mboms": true,
    "include_baselines": false,
    "continue_on_error": false,
    "rollback_on_failure": true,
    "dry_run": false
  }' | jq .
```

回滚行为：

- 仅在 `abort=true`（发生失败且停止）时触发
- 回滚顺序：先 MBOM reopen，再 Routing reopen
- `results[]` 会追加 `mbom_reopen` / `routing_reopen` 的记录，状态为：
  - `rolled_back`：回滚成功
  - `rollback_failed`：回滚失败（需要人工处理）

## 3) 结果解读（results[].status）

常见状态：

- `planned`：dry-run 计划执行
- `executed`：已执行 release
- `failed`：release 调用失败（message 会带原因）
- `skipped_already_released`：已 released，跳过
- `skipped_errors`：diagnostics 有 errors，跳过（baseline 可用 `baseline_force=true` 强制）
- `blocked_esign_incomplete`：电子签名清单不完整，baseline release 被阻止
- `rolled_back` / `rollback_failed`：回滚结果（仅当开启 rollback）

每个 step 都带 `diagnostics`：

- `diagnostics.ok`：本 step 的诊断是否无 errors
- `diagnostics.errors[]` / `diagnostics.warnings[]`：结构化问题清单（用于 UI/排障）

执行结束后会 best-effort 返回 `post_readiness`，用于确认“发布后 readiness 是否改善”。

## 4) 常见错误

- `403 Admin permission required`：当前用户不是 admin/superuser
- `404 Item <id> not found`：item_id 不存在
- `400`：
  - ruleset 不存在或不适用于对应 kind（routing_release/mbom_release/baseline_release）
  - `rollback_on_failure=true` 但 `continue_on_error=true`（不允许）

## 5) E2E 测试 Failpoint（仅测试用）

为了覆盖回滚路径，支持用 header 注入失败（仅当 `YUANTUS_TEST_FAILPOINTS_ENABLED=true`）。

- Header：`x-yuantus-failpoint`
- 候选值示例：
  - `routing_release:<routing_id>`
  - `mbom_release:<mbom_id>`
  - `baseline_release:<baseline_id>`
  - `routing:<routing_id>` / `mbom:<mbom_id>` / `baseline:<baseline_id>`

说明：Failpoint 只用于测试环境，生产不要开启。

