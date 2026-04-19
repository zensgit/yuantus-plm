# P2 Shared-dev First-run Checklist

日期：2026-04-19

## 目的

这份清单把 shared-dev **第一次初始化 + 第一次 observation 回归** 固定成单条路径。

适用场景：

- fresh shared-dev
- 第一次生成 admin / ops-viewer 凭证
- 第一次执行：
  - `precheck_p2_observation_regression.sh`
  - `run_p2_observation_regression.sh`

不适用场景：

- 已经稳定运行、只需要常规 rerun 的 shared-dev
- 已承载真实业务数据且不能执行 bootstrap fixture 初始化的环境

## 执行前提

- 所有相对路径命令都从 **仓库根目录** 执行
- 操作者同时具备：
  - 本地仓库访问权限
  - shared-dev 远端部署权限
  - `docker compose` 执行权限

## 最终执行顺序

### 1. 本地先生成两份 env

```bash
scripts/generate_p2_shared_dev_bootstrap_env.sh \
  --base-url "https://change-me-shared-dev-host"
```

这里的 `change-me-shared-dev-host` 必须先替换成真实 shared-dev 域名或网关地址，再继续第 2 步。

默认生成：

- `$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env`
- `$HOME/.config/yuantus/p2-shared-dev.env`

### 2. 本地先校验 env

```bash
scripts/validate_p2_shared_dev_env.sh
```

如果这里失败，不要继续碰远端。

### 3. 把 bootstrap env 传到 shared-dev 服务器

```bash
scp "$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env" \
  <user>@<server-host>:<server-repo>/deployments/docker/shared-dev.bootstrap.env
```

如果不是 `scp`，也必须用等价的安全通道把该文件放到远端：

- `<server-repo>/deployments/docker/shared-dev.bootstrap.env`

### 4. 在 shared-dev 服务器执行 one-shot bootstrap

```bash
cd <server-repo>
docker compose -f docker-compose.yml --env-file ./deployments/docker/shared-dev.bootstrap.env \
  --profile bootstrap run --rm bootstrap
```

这里明确固定到仓库跟踪的 `docker-compose.yml`。fresh shared-dev first-run 不应隐式依赖任何机器本地的 `docker-compose.override.yml`。

预期：

- migrations 完成
- `admin`
- `ops-viewer`
- meta
- `p2-observation` fixture

### 5. 启动常驻服务

```bash
docker compose -f docker-compose.yml up -d api worker
```

### 6. 做最小存活检查

```bash
docker compose ps
curl -fsS http://127.0.0.1:7910/api/v1/health
```

### 7. 回到操作机，再校验 observation env

```bash
scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "$HOME/.config/yuantus/p2-shared-dev.env"
```

### 8. 先跑 precheck

```bash
scripts/precheck_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

预期至少有：

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary_probe.json`

如果 precheck 不绿，不要继续 full regression。

### 9. precheck 通过后再跑 canonical wrapper

```bash
OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)" \
ARCHIVE_RESULT=1 \
scripts/run_p2_observation_regression.sh \
  --env-file "$HOME/.config/yuantus/p2-shared-dev.env"
```

### 10. 最低回传物

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary_probe.json`
- `summary.json`
- `items.json`
- `anomalies.json`
- `export.csv`
- `README.txt`
- `OBSERVATION_RESULT.md`
- `${OUTPUT_DIR}.tar.gz`

## 期望基线

bootstrap 成功后，第一次 observation 预期接近：

- baseline:
  - `pending=1`
  - `overdue=2`
  - `escalated=0`
- after one `escalate-overdue`:
  - `pending=1`
  - `overdue=3`
  - `escalated=1`

如果在这之后又继续执行任何写接口验证，例如：

- `admin -> auto-assign-approvers`
- 额外的 `escalate-overdue`
- 其他会新增 / 迁移 approval 的 write smoke

那么旧的 frozen baseline 就已经失效。  
此时不要再把 earlier baseline 用作后续 readonly rerun 的对比基线，而应：

1. 先在“所有允许的写操作都完成之后”重新跑一次只读 observation
2. 把这次最新结果冻结成新的 readonly baseline
3. 之后所有常规 rerun 都对比这份新基线

## 快速入口

如果只想直接拿命令，不看正文：

```bash
bash scripts/print_p2_shared_dev_first_run_commands.sh
```
