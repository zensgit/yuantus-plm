# DEV / Verification - Shared-dev Docker Bootstrap

日期：2026-04-19

## 目标

补齐 `docker-compose.yml` 中缺失的 shared-dev 初始化路径，让远端部署首次启动后可以一次性完成：

- `db upgrade`
- identity migrations
- `seed-identity admin`
- `seed-identity ops-viewer`
- `seed-meta`
- `yuantus seed-data`（generic demo seed，不等同于 P2 observation 专用 fixture）

并把后续 `p2` observation 回归需要的本地 env 文件约定固定下来。

## 改动

1. `Dockerfile`
   - 追加复制：
     - `scripts/`
   - 让容器内能执行 bootstrap 脚本。

2. `scripts/bootstrap_shared_dev.sh`
   - 新增一次性 bootstrap 脚本
   - 使用 compose env 驱动 tenant/org/admin/viewer 初始化
   - 允许跳过 `seed-meta` 或 sample data

3. `docker-compose.yml`
   - 新增 profile 化的一次性服务 `bootstrap`
   - 明确注入 bootstrap 所需 env
   - 不自动绑定到每次 API 重启，避免重复 seed

4. `deployments/docker/shared-dev.bootstrap.env.example`
   - 新增 shared-dev bootstrap env 模板

5. `README.md`
   - 新增 shared-dev bootstrap 章节
   - 说明 bootstrap、长驻服务启动、以及本地 `p2-shared-dev.env` 的衔接方式

## 预期结果

shared-dev 的首次初始化不再依赖手工拼接 seed 命令，也不再需要先猜测 `USERNAME/PASSWORD / TENANT_ID / ORG_ID`。

完成 bootstrap 后，运维或测试只需要：

1. 用 bootstrap 设定好的 admin 凭证写入本地 `~/.config/yuantus/p2-shared-dev.env`
2. 执行 precheck
3. 执行正式 observation regression

## 已知边界

这次补的是 deployment/bootstrap 闭环，不是 P2 observation 业务 fixture 产品化。

- `yuantus seed-data` 只提供 generic Part/Document/BOM demo 数据
- 如果要把 shared-dev 当作 observation 回归基线，仍需要额外准备 ECO overdue/escalation fixtures
