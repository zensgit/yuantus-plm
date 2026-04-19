# DEV / Verification - Shared-dev P2 Observation Bootstrap E2E

日期：2026-04-19

## 背景

`shared-dev bootstrap` 第一版已经补上了 docker / compose / env / bootstrap 服务入口，但真正把它放到 fresh sqlite 环境里跑时，暴露了两个实际问题：

1. `seed-identity` 只会把 `admin` / `ops-viewer` 写进 auth 表和 membership，`seed-meta` 只保证 `admin` 出现在业务库 `rbac_users`。
2. `scripts/bootstrap_shared_dev.sh` 直接调用 `yuantus` console script；本地 `.venv` 的 shebang 漂移时，这条路径会在真正验证前就失败。

如果不把这两点收口，shared-dev 初始化仍然不是“开箱即用”的 bootstrap 闭环。

## 本轮开发

### 1. `scripts/seed_p2_observation_fixtures.py`

- 新增 `--admin-username` / `--viewer-username`
- 新增 `ensure_rbac_user(...)`
- 在 seed fixture 前显式 materialize：
  - `RBACUser(id=1, user_id=1, username=admin, is_superuser=true)`
  - `RBACUser(id=2, user_id=2, username=ops-viewer, is_superuser=false)`
- 同时绑定：
  - `admin -> engineer`
  - `ops-viewer -> ops-viewer`

结果是：fresh shared-dev 不再需要任何 local-dev 专用预热步骤，`p2-observation` dataset 自己就能把业务库 RBAC 身份补齐。

### 2. `scripts/bootstrap_shared_dev.sh`

- 所有 CLI 调用统一改成：
  - `python -m yuantus ...`
- 新增向 fixture seeder 传递：
  - `--admin-username`
  - `--viewer-username`
- bootstrap 输出里追加：
  - `ops-viewer` 凭证
  - dataset mode
  - fixture manifest 路径

这让同一套脚本在：
- 容器里
- 本地 `.venv`
- 临时回归 sqlite

三种场景下都能走同一条初始化路径。

### 3. 文档

更新了：

- `README.md`
- `docs/DEV_AND_VERIFICATION_SHARED_DEV_BOOTSTRAP_DOCKER_20260419.md`

重点写清：

- 默认 dataset 已是 `p2-observation`
- bootstrap 会 materialize `admin / ops-viewer` 的本地 RBACUser
- `ops-viewer` 可直接用于 `403` 分支 smoke

## 验证环境

- worktree:
  - `/tmp/yuantus-p2-observation-bootstrap`
- 临时数据库:
  - `/tmp/yuantus-p2-observation-bootstrap/tmp/p2-bootstrap-e2e-20260419/yuantus.db`
- API:
  - `http://127.0.0.1:7921`
- 凭证:
  - `admin / admin`
  - `ops-viewer / ops123`
- tenant/org:
  - `tenant-1 / org-1`

## 实际验证步骤

本轮不是只做静态检查，而是跑了完整的本地闭环：

1. `bootstrap_shared_dev.sh`
   - migrations
   - `seed-identity admin`
   - `seed-identity ops-viewer`
   - `seed-meta`
   - `seed_p2_observation_fixtures.py`
2. 启动 uvicorn
3. admin 登录
4. 跑 baseline：
   - `scripts/verify_p2_dev_observation_startup.sh`
   - `scripts/render_p2_observation_result.py`
5. 触发：
   - `POST /api/v1/eco/approvals/escalate-overdue`
6. 跑 after-escalate：
   - `scripts/verify_p2_dev_observation_startup.sh`
   - `scripts/render_p2_observation_result.py`
7. 跑差异与评估：
   - `scripts/compare_p2_observation_results.py`
   - `scripts/evaluate_p2_observation_results.py`
8. 重置 fixture
9. 验证权限三态：
   - unauthenticated -> `401`
   - `ops-viewer` -> `403`
   - `admin` -> `200`

## 验证结果

### 1. baseline

- `pending_count=1`
- `overdue_count=2`
- `escalated_count=0`

### 2. after one `escalate-overdue`

- `pending_count=1`
- `overdue_count=3`
- `escalated_count=1`

### 3. permission tri-state

- unauthenticated -> `401`
- `ops-viewer` -> `403`
- `admin` -> `200`

### 4. compare / eval

状态变更评估已通过，命中预期 delta：

- `overdue_count=+1`
- `escalated_count=+1`
- `items_count=+1`
- `export_json_count=+1`
- `export_csv_rows=+1`
- `overdue_not_escalated=-1`
- `escalated_unresolved=+1`

## 产物

- baseline:
  - `/tmp/yuantus-p2-observation-bootstrap/tmp/p2-bootstrap-e2e-20260419/baseline/OBSERVATION_RESULT.md`
- after-escalate:
  - `/tmp/yuantus-p2-observation-bootstrap/tmp/p2-bootstrap-e2e-20260419/after-escalate/OBSERVATION_RESULT.md`
  - `/tmp/yuantus-p2-observation-bootstrap/tmp/p2-bootstrap-e2e-20260419/after-escalate/OBSERVATION_DIFF.md`
  - `/tmp/yuantus-p2-observation-bootstrap/tmp/p2-bootstrap-e2e-20260419/after-escalate/OBSERVATION_EVAL.md`
- fixture manifest:
  - `/tmp/yuantus-p2-observation-bootstrap/tmp/p2-bootstrap-e2e-20260419/p2_observation_fixture_manifest.json`
- permission tri-state:
  - `/tmp/yuantus-p2-observation-bootstrap/tmp/p2-bootstrap-e2e-20260419/permissions/status.txt`

## 结论

这条 shared-dev bootstrap 线现在已经真正闭环：

- 能初始化 auth + meta + P2 observation fixtures
- 能在 fresh 环境里自补 `admin / ops-viewer` 的本地 RBACUser
- baseline / after-escalate 指标与本地审计目标一致
- `401 / 403 / 200` 权限三态成立

换句话说，后续如果要在 shared-dev / 远端环境里跑：

- `precheck_p2_observation_regression.sh`
- `run_p2_observation_regression.sh`

现在缺的就不再是“怎么初始化”，而只剩真实 shared-dev URL/凭证本身。
