# Remote Deployment Remediation

**Date:** 2026-04-18
**Target host:** `142.171.239.56`
**Target service:** `Yuantus` P2 observation environment
**Repo baseline:** `6fd28be`

## Summary

本次目标是在远端主机上部署一个可独立运行的 `Yuantus` P2 observation 环境，并完成：

- `scripts/verify_p2_dev_observation_startup.sh`
- `scripts/render_p2_observation_result.py`
- 读出 `OBSERVATION_RESULT.md`

最终结果：

- 远端已成功运行独立容器 `yuantus-p2-api`
- 服务监听 `127.0.0.1:7910`
- 读路径 smoke 已通过
- 写路径验证已通过：
  - `ops-viewer -> auto-assign` 返回 `403`
  - `admin -> auto-assign` 返回 `200`
  - `admin -> escalate-overdue` 返回 `200`
- 观察结果已成功重渲染

## Symptoms and Impact

部署过程中实际遇到的阻塞点有 4 类：

1. 远端主机缺少可直接使用的 Python 开发环境
   - `python3 -m venv` 失败
   - 主机无 `pip`
   - `mainuser` 无免密 `sudo`

2. 首轮大目录同步不稳定
   - 远端工作目录缺失关键源码文件
   - 典型缺失：
     - `src/yuantus/__init__.py`
     - `src/yuantus/cli.py`
     - `src/yuantus/meta_engine/bootstrap.py`

3. macOS 元数据文件污染迁移目录
   - 远端出现 `migrations/._*.py`
   - `alembic upgrade` 报：
     - `SyntaxError: source code string cannot contain null bytes`

4. 重新基于最小目录 build 新镜像时触发离线 wheel 不完整问题
   - Dockerfile 命中 `/wheels/*.whl` 后走离线安装
   - 实际缺少 `charset-normalizer==3.4.4`
   - build 失败

这些问题导致“直接按本机 `local-dev-env/start.sh` 思路远端复刻”无法一次成功。

## Environment and Change Context

远端使用的是独立目录，不污染已有 `metasheet2` 部署：

- 工作目录：`/home/mainuser/Yuantus-p2-mini`
- 结果目录：`/home/mainuser/Yuantus-p2-mini/local-dev-env/results`
- 数据库：`/home/mainuser/Yuantus-p2-mini/local-dev-env/data/yuantus.db`
- 容器：`yuantus-p2-api`

运行策略没有依赖远端系统 Python，而是复用已构建成功的镜像：

- 镜像：`yuantus-p2-local:20260418`
- 代码通过 bind mount 挂载到容器内 `/work`
- `PYTHONPATH=/work/src`
- `YUANTUS_DATABASE_URL=sqlite:////work/local-dev-env/data/yuantus.db`
- `YUANTUS_TENANCY_MODE=disabled`
- `YUANTUS_IDENTITY_DATABASE_URL=` 空值

## Root Cause

已确认的直接原因如下：

1. 远端主机不具备本机脚本所假设的 Python 运行前提
   - `local-dev-env/start.sh` 依赖可用的本地 Python、`venv`、`pip`
   - 远端主机不满足这一假设

2. 首轮大体积同步夹带大量无关产物，且同步结果不完整
   - 关键源码文件未稳定落地
   - 继续在该目录上排障成本高

3. 从 macOS 打包/传输时把 AppleDouble 元数据 `._*` 一并带到 Linux
   - `alembic` 会把这些文件当成 migration 脚本扫描
   - 因二进制内容触发 null byte / decode 错误

4. 最小目录重建镜像时触发 Dockerfile 的“有 wheel 就强制离线安装”路径
   - wheel 缓存并不完整
   - 因此不适合在当前远端目录再次重建

## Remediation

本次实际采用的修复路径如下。

### 1. 放弃远端主机 Python 方案，改为 Docker 方案

不再尝试在远端安装 `.venv`，直接复用已有可工作的容器镜像，并把代码挂载进去运行。

### 2. 放弃不稳定的大目录，切换到最小工作目录

新建独立目录：

- `/home/mainuser/Yuantus-p2-mini`

只放运行 observation 所需最小文件集：

- `src/`
- `migrations/`
- `migrations_identity/`
- `plugins/`
- `scripts/verify_p2_dev_observation_startup.sh`
- `scripts/render_p2_observation_result.py`
- `local-dev-env/scripts/seed_data.py`
- `local-dev-env/start.sh`
- 相关基础 root files

### 3. 清理 macOS 元数据污染

在远端删除：

- `find /home/mainuser/Yuantus-p2-mini -name '._*' -delete`
- `find /home/mainuser/Yuantus-p2-mini -name '.DS_Store' -delete`

这一步是让 `alembic` 恢复可读迁移目录的关键修复。

### 4. 一次性 seed 容器执行迁移和样本初始化

按 `local-dev-env/start.sh` 的语义，先执行：

- `db upgrade`
- `seed-identity admin`
- `seed-identity ops-viewer`
- `seed-meta`
- `local-dev-env/scripts/seed_data.py`

### 5. 再起常驻 API 容器

常驻容器命令为：

```bash
python -m uvicorn yuantus.api.app:app --host 0.0.0.0 --port 7910
```

这样宿主机可以通过 `127.0.0.1:7910` 访问。

## Verification

### Read path

`verify_p2_dev_observation_startup.sh` 已通过，以下端点全部 `200`：

- `GET /api/v1/eco/approvals/dashboard/summary`
- `GET /api/v1/eco/approvals/dashboard/items`
- `GET /api/v1/eco/approvals/dashboard/export?fmt=json`
- `GET /api/v1/eco/approvals/dashboard/export?fmt=csv`
- `GET /api/v1/eco/approvals/audit/anomalies`

### Baseline rendered result

首次渲染结果显示：

- `pending_count=1`
- `overdue_count=2`
- `escalated_count=0`
- `total_anomalies=2`
- `overdue_not_escalated=2`
- `escalated_unresolved=0`

### Write path

写路径验证结果：

- `ops-viewer -> POST /api/v1/eco/{eco-specialist}/auto-assign-approvers`
  - HTTP `403`
  - `{"detail":"Forbidden: insufficient ECO permission"}`

- `admin -> POST /api/v1/eco/{eco-specialist}/auto-assign-approvers`
  - HTTP `200`
  - 成功分派 `admin`

- `admin -> POST /api/v1/eco/approvals/escalate-overdue`
  - HTTP `200`
  - `escalated=1`
  - 命中 `eco-overdue-opsview`

### Re-rendered observation result

写路径后再次渲染结果：

- `pending_count=2`
- `overdue_count=3`
- `escalated_count=1`
- `total_anomalies=2`
- `escalated_unresolved=1`
- `overdue_not_escalated=1`
- `no_candidates=0`

这说明预期的状态迁移已发生：

- 一条记录从 `overdue_not_escalated` 迁移到 `escalated_unresolved`

### Final artifact path

最终观察结果文件：

- `/home/mainuser/Yuantus-p2-mini/local-dev-env/results/OBSERVATION_RESULT.md`

## Residual Risks and Follow-ups

1. 当前 sqlite 文件由容器内 `root` 写入
   - 远端文件属主目前是 `root`
   - 若后续需要由 `mainuser` 直接修改或清理，可能要补 `chown`

2. macOS 到 Linux 的传输链路需要显式排除：
   - `._*`
   - `.DS_Store`

3. Dockerfile 的 wheel 检测逻辑过于乐观
   - 只要 `/wheels` 非空就强制离线安装
   - 建议后续改成：
     - wheel 完整性校验通过后再离线
     - 否则回退在线安装

4. 本次是 `local-dev-env` 语义
   - 它证明“工具链与状态语义可跑通”
   - 不等同于 shared-dev 真实观察基线

5. 可沉淀为长期 runbook 的内容：
   - 远端最小目录部署方式
   - Docker-only recovery 路径
   - macOS 元数据清理策略

已沉淀的操作文档：

- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
