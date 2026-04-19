# DEV / Verification - Shared-dev Docker Bootstrap

日期：2026-04-19

## 目标

补齐 `docker-compose.yml` 中缺失的 shared-dev 初始化路径，让远端部署首次启动后可以一次性完成：

- `db upgrade`
- identity migrations
- `seed-identity admin`
- `seed-identity ops-viewer`
- `seed-meta`
- `scripts/seed_p2_observation_fixtures.py`

并把后续 `p2` observation 回归需要的本地 env 文件约定固定下来。

## 改动

1. `Dockerfile`
   - 追加复制：
     - `scripts/`
   - 让容器内能执行 bootstrap 脚本。

2. `scripts/bootstrap_shared_dev.sh`
   - 新增一次性 bootstrap 脚本
   - 使用 compose env 驱动 tenant/org/admin/viewer 初始化
   - 支持 `YUANTUS_BOOTSTRAP_DATASET_MODE=none|generic|p2-observation`
   - 默认走 `p2-observation`
   - 输出 fixture manifest 路径，供后续 write smoke 直接复用

3. `docker-compose.yml`
   - 新增 profile 化的一次性服务 `bootstrap`
   - 明确注入 bootstrap 所需 env
   - 不自动绑定到每次 API 重启，避免重复 seed

4. `deployments/docker/shared-dev.bootstrap.env.example`
   - 新增 shared-dev bootstrap env 模板

5. `scripts/seed_p2_observation_fixtures.py`
   - 将未跟踪的 `local-dev-env/scripts/seed_data.py` 产品化为受控脚本
   - 现在会自补本地业务库里的 `RBACUser(admin / ops-viewer)`，不再依赖 local-dev 预热
   - 固定 4 条 ECO：
     - `eco-pending`
     - `eco-overdue-admin`
     - `eco-overdue-opsview`
     - `eco-specialist`
   - 预期基线：
     - `pending=1`
     - `overdue=2`
     - `escalated=0`
   - 预期单次 `escalate-overdue` 后：
     - `pending=1`
     - `overdue=3`
     - `escalated=1`

6. `README.md`
   - 新增 shared-dev bootstrap 章节
   - 说明 bootstrap、长驻服务启动、以及本地 `p2-shared-dev.env` 的衔接方式

## 预期结果

shared-dev 的首次初始化不再依赖手工拼接 seed 命令，也不再需要先猜测 `USERNAME/PASSWORD / TENANT_ID / ORG_ID`。

完成 bootstrap 后，运维或测试只需要：

1. 用 bootstrap 设定好的 admin 凭证写入本地 `~/.config/yuantus/p2-shared-dev.env`
2. 执行 precheck
3. 执行正式 observation regression

如果要补做 `401 / 403 / 200` 三态 smoke，bootstrap 输出里还会带出 `ops-viewer` 的用户名和密码。

## 已知边界

- `p2-observation` dataset 仍假设 bootstrap 目标用户 id 为 `1/2`，但不再要求 viewer 的 `RBACUser` 预先存在
- 该脚本会清空现有 `ECOApproval` / `ECO`，因此只适合 fresh shared-dev 初始化，不适合已承载真实业务数据的环境
