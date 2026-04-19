# DEV / Verification - Shared-dev 142 First-run Execution

日期：2026-04-19

## 背景

这次不是本地 dry-run，而是在真实远端 `142` 上执行 `shared-dev` 首次初始化，并把：

- bootstrap
- health check
- precheck
- baseline observation
- `escalate-overdue`
- after-escalate diff / eval
- 写接口权限三态

整条链跑通。

执行目标是确认：仓库里已经合入的 `shared-dev bootstrap / first-run / observation` 工具链，能在真实远端环境里落地，而不是只在本地 worktree 里成立。

## 目标环境

- remote host:
  - `142.171.239.56`
- ssh user:
  - `mainuser`
- remote deploy dir:
  - `/home/mainuser/Yuantus-p2-observation`
- operator repo:
  - `/Users/chouhua/Downloads/Github/Yuantus`

本轮将 `142` 视作 fresh shared-dev，并明确允许 reset。

## 执行前准备

### 1. 本地生成 env

已生成：

- bootstrap env:
  - `$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env`
- observation env:
  - `$HOME/.config/yuantus/p2-shared-dev.env`

最终 operator-side `BASE_URL` 使用公网地址：

- `http://142.171.239.56:7910`

### 2. 远端备份

执行前已备份原远端 deploy 关键文件：

- `.env`
- `deployments/docker/shared-dev.bootstrap.env`
- `docker-compose.override.yml`

备份目录：

- `/home/mainuser/backups/yuantus-shared-dev-20260419-092731`

### 3. 代码同步

本地最新 `main` 已通过 `rsync` 同步到远端 deploy 目录。

## 真实执行过程

### 1. reset 远端 compose 环境

执行：

- `docker compose down -v --remove-orphans`

### 2. 处理远端构建 blocker

首次 `docker compose build bootstrap api worker` 被远端残缺 wheelhouse 挡住：

- `vendor/wheels` 非空时 Dockerfile 会强制离线安装
- 但 wheelhouse 缺失 `charset-normalizer==3.4.4`

远端临时处理：

- 将原目录移走：
  - `vendor/wheels.offline-20260419-093006`
- 重新创建空的 `vendor/wheels/`

之后 build 通过。

### 3. 上传 bootstrap env

最初是先 `scp` 再 `rsync --delete`，导致 env 被同步过程删掉。  
已修正为：代码同步后重新上传。

最终远端文件：

- `/home/mainuser/Yuantus-p2-observation/deployments/docker/shared-dev.bootstrap.env`

### 4. 运行 bootstrap

执行成功：

- `docker compose --env-file ./deployments/docker/shared-dev.bootstrap.env --profile bootstrap run --rm bootstrap`

成功完成：

- main DB migrations
- identity migrations
- `admin`
- `ops-viewer`
- `seed-meta`
- `p2-observation` fixture seed

bootstrap 输出的目标基线与代码预期一致：

- baseline:
  - `pending=1`
  - `overdue=2`
  - `escalated=0`
- after one `escalate-overdue`:
  - `pending=1`
  - `overdue=3`
  - `escalated=1`

### 5. 拉起常驻服务时遇到的两个远端前置

`docker compose up -d api worker` 首次失败，原因不是应用代码，而是远端现存部署前置不完整：

1. `docker-compose.override.yml` 依赖外部网络：
   - `cad-ml-network`
2. `docker-compose.override.yml` 依赖宿主机 secret 文件：
   - `/Users/huazhou/.config/yuantus/athena_client_secret`

这两项都不是本轮 P2 observation first-run 的必需前提。

同时还暴露出一个 runtime 配置不一致：

- `bootstrap` 走基础 compose，identity DB 默认是 `yuantus_identity`
- `api/worker` 通过 override 被改成 `yuantus_identity_mt_pg`

为避免把远端 first-run 变成另一个基础设施修复任务，本轮最终采用：

- `docker compose -f docker-compose.yml up -d api worker`

也就是让 runtime 与成功执行的 bootstrap 使用同源基础 compose 配置。

### 6. 清掉旧容器端口占用

端口 `7910` 还被旧容器占用：

- `yuantus-p2-api`

已停止并移除旧容器后，基础 compose 的 `api/worker` 启动成功。

### 7. health check

通过：

- remote:
  - `curl http://127.0.0.1:7910/api/v1/health`
- operator machine:
  - `curl http://142.171.239.56:7910/api/v1/health`

返回：

- `ok=true`
- `tenancy_mode=db-per-tenant-org`
- `schema_mode=migrations`

## 真实回归结果

### 1. precheck

执行：

- `scripts/precheck_p2_observation_regression.sh --env-file "$HOME/.config/yuantus/p2-shared-dev.env"`

结果：

- `SUMMARY_HTTP_STATUS=200`

产物：

- `tmp/p2-observation-precheck-20260419-173952/OBSERVATION_PRECHECK.md`
- `tmp/p2-observation-precheck-20260419-173952/observation_precheck.json`
- `tmp/p2-observation-precheck-20260419-173952/summary_probe.json`

### 2. baseline observation

执行：

- `scripts/run_p2_observation_regression.sh --env-file "$HOME/.config/yuantus/p2-shared-dev.env"`

baseline 结果：

- `pending_count=1`
- `overdue_count=2`
- `escalated_count=0`
- `items_count=3`
- `overdue_not_escalated=2`
- `escalated_unresolved=0`

产物：

- `tmp/p2-shared-dev-observation-20260419-174003/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-observation-20260419-174003.tar.gz`

### 3. 写接口权限三态 + 最小状态变化

本轮实际验证了两条写接口。

#### `POST /api/v1/eco/approvals/escalate-overdue`

- unauthenticated:
  - `401`
- `ops-viewer`:
  - `403`
- `admin`:
  - `200`

#### `POST /api/v1/eco/{eco-specialist}/auto-assign-approvers`

- unauthenticated:
  - `401`
- `ops-viewer`:
  - `403`
- `admin`:
  - `200`

注意：

- `admin -> auto-assign` 是在 after-escalate 状态采集之后补打，用于补齐权限三态，不参与本轮 diff/eval 基线计算。

写路径回传文件在：

- `tmp/p2-shared-dev-observation-20260419-174003/write-checks/`

### 4. after-escalate observation

在执行一次：

- `POST /api/v1/eco/approvals/escalate-overdue`

之后，重新跑 observation wrapper，并生成 diff / eval。

after-escalate 结果：

- `pending_count=1`
- `overdue_count=3`
- `escalated_count=1`
- `items_count=4`
- `overdue_not_escalated=1`
- `escalated_unresolved=1`

差异命中预期：

- `overdue_count=+1`
- `escalated_count=+1`
- `items_count=+1`
- `export_json_count=+1`
- `export_csv_rows=+1`
- `overdue_not_escalated=-1`
- `escalated_unresolved=+1`

评估结果：

- `OBSERVATION_EVAL.md`
  - verdict: `PASS`
  - checks: `17/17`

产物：

- `tmp/p2-shared-dev-observation-20260419-174003-after-escalate/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-observation-20260419-174003-after-escalate/OBSERVATION_DIFF.md`
- `tmp/p2-shared-dev-observation-20260419-174003-after-escalate/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-observation-20260419-174003-after-escalate.tar.gz`

## 结论

`142` 这次已经不只是“能部署”，而是完成了真实 `shared-dev` first-run 执行闭环：

- bootstrap 成功
- 常驻服务成功
- precheck 成功
- baseline 观察面成功
- `escalate-overdue` 状态迁移成功
- diff / eval 通过
- 两条写接口 `401 / 403 / 200` 三态成立

本轮最重要的事实有两个：

1. 仓库内的 `shared-dev` bootstrap / observation 工具链在真实远端上成立。
2. 真实执行过程中暴露的阻塞主要是部署前置和 compose runtime 偏差，不是 P2 observation 代码语义问题。

## 本轮保留的远端操作注意点

1. 当前 `142` 的可用运行路径是：
   - bootstrap: 默认 compose
   - runtime: `docker compose -f docker-compose.yml up -d api worker`

2. 远端 `vendor/wheels` 当前被临时清空，原目录已移到：
   - `vendor/wheels.offline-20260419-093006`

3. 远端 `docker-compose.override.yml` 仍然包含：
   - `cad-ml-network`
   - Athena secret file
   - `yuantus_identity_mt_pg`

   这些属于后续环境治理事项，不影响本次 first-run / observation 结果成立。
