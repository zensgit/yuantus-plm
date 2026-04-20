# DEV / Verification - CAD Backend Profile Shared-dev 142 Smoke

日期：2026-04-20

## 目标

确认 shared-dev `142` 当前已部署服务，是否已经具备 CAD backend profile 的请求面，足以承接 PR `#288` 的远端 smoke。

## 执行边界

- 本轮不是远端部署。
- 当前没有可用 SSH 入口，也没有仓库内定义好的“非 reset 分支部署到 142”正式路径。
- 所以本轮只能验证 `142` 现网 API，不代表 `PR #288` 的服务端代码已经部署到 `142`。

## 执行方式

### 1. 直接跑 verifier

使用 shared-dev bootstrap 保留的 admin 凭证，对 `142` 执行：

```bash
BASE_URL="http://142.171.239.56:7910" \
TENANT_ID="tenant-1" \
ORG_ID="org-1" \
LOGIN_USERNAME="<bootstrap-admin>" \
PASSWORD="<bootstrap-admin-password>" \
RUN_TENANT_SCOPE=1 \
bash scripts/verify_cad_backend_profile_scope.sh
```

结果：

- login: `200`
- `GET /api/v1/cad/backend-profile`: `404`
- verifier 在第一步即停止，无法进入 `PUT -> capabilities -> restore`

失败产物：

- `tmp/cad-backend-profile-142-smoke-20260420-173758/`

### 2. 补充 sanitized 探针

为避免保留带密码的临时文件，额外生成了一个不含凭证的结果包，只记录接口存在性和状态码。

产物：

- `tmp/cad-backend-profile-142-sanitized-20260420-174219/summary_report.json`

## 结果

| 探针 | 结果 | 解释 |
| --- | --- | --- |
| `GET /api/v1/health` | `200` | 远端服务在线 |
| `POST /api/v1/auth/login` | `200` | admin 凭证有效 |
| unauth `GET /api/v1/cad/backend-profile` | `401` | 请求被鉴权层拦截 |
| admin `GET /api/v1/cad/backend-profile` | `404` | 远端当前服务没有该读面 |
| `/openapi.json` 含 `/api/v1/cad/backend-profile` | `false` | 远端未部署该路由 |
| admin `GET /api/v1/cad/capabilities` | `200` | CAD capabilities 端点存在 |
| `/openapi.json` 含 `/api/v1/cad/capabilities` | `true` | 远端 CAD capabilities 已部署 |
| `integrations.cad_connector.profile` | 缺失 | 远端 capabilities shape 仍是旧版 |

`summary_report.json` 摘要：

```json
{
  "health_status": 200,
  "login_status": 200,
  "backend_profile": {
    "noauth_status": 401,
    "admin_status": 404,
    "present_in_openapi": false
  },
  "capabilities": {
    "status": 200,
    "present_in_openapi": true,
    "has_profile_block": false
  }
}
```

## 结论

shared-dev `142` 当前运行的服务版本，尚未包含 CAD backend profile 的公开请求面：

1. `/api/v1/cad/backend-profile` 不在远端 OpenAPI 中。
2. `/api/v1/cad/capabilities` 仍返回旧 shape，`integrations.cad_connector.profile` 不存在。
3. 因此，PR `#288` 不能在 `142` 上完成有效远端 smoke；当前能证明的只有远端仍在线、可登录、且 CAD capabilities 老接口仍可用。

## 对 PR #288 的影响

- F1 `verifier failure-path restore`
  - 远端无法验证，因为 verifier 在第一步 `GET /backend-profile` 即被 `404` 阻断。
  - 当前只有本地 clean worktree contract test 和 focused pytest 作为证据。
- F2 `PUT requires admin` 测试补齐
  - 远端无法验证，因为 backend-profile 路由本身未部署。
  - 当前只有本地 router test 作为证据。
- F4 `worker tenant context fail-loud`
  - 远端更无法验证；它本来就要求新代码已部署，且还要能故意构造缺 `tenant_id/org_id` 的 job payload。

## 下一步

要在 `142` 上继续做 PR `#288` 的真实 smoke，前提是先把包含 CAD backend profile 请求面的代码部署到 `142`。在当前仓库和当前访问条件下，这一步没有可执行的非破坏性入口。

所以当前收口应是：

1. 保留本地 clean worktree `31 passed` 作为主验证。
2. 把这次 `142` 结果记为“远端环境版本落后，smoke blocked”，而不是“代码 smoke failed”。
3. 等有正式远端部署入口或 `142` 升到包含 `/api/v1/cad/backend-profile` 的版本后，再重跑同一条 verifier。
