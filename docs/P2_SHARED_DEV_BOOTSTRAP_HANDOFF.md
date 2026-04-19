# P2 Shared Dev Bootstrap Handoff

日期：2026-04-19

## 目标

这份 handoff 用于把 **fresh shared-dev 初始化** 交给持有远端部署权限的操作者执行。

如果你只需要一份单页执行顺序，直接看：

- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`
- `scripts/print_p2_shared_dev_first_run_commands.sh`

它解决的是：

- 如何在远端第一次把 `tenant / org / admin / ops-viewer / meta / p2-observation fixture` 初始化出来
- 如何把 bootstrap 结果衔接到本地：
  - `precheck_p2_observation_regression.sh`
  - `run_p2_observation_regression.sh`

它不解决：

- 远端机器准备 Docker / Compose 本身
- 真实长期 secret 管理
- 已承载真实业务数据环境上的安全回放

## 前提

操作者需要：

- 可访问 shared-dev 主机或部署目录
- 可执行：
  - `docker compose`
- 可修改 bootstrap env 文件
- 知道最终访问地址：
  - `BASE_URL`

不要把真实密码提交进仓库。  
如果要落本地 env 文件，放在仓库外，例如：

- `$HOME/.config/yuantus/p2-shared-dev.env`

并设置 `0600`。

## 关键文件

### 1. 服务器侧 bootstrap env

来源模板：

- `deployments/docker/shared-dev.bootstrap.env.example`

用途：

- 只用于远端/shared-dev 的一次性初始化

### 2. 操作机侧 observation env

建议路径：

- `$HOME/.config/yuantus/p2-shared-dev.env`

用途：

- 只用于本地执行 precheck / regression wrapper

## 推荐执行顺序

所有相对路径命令都默认从 **仓库根目录** 执行。

### 0. 首选：先用 helper 生成两份 env

```bash
scripts/generate_p2_shared_dev_bootstrap_env.sh \
  --base-url "https://change-me-shared-dev-host"
```

这里的 `change-me-shared-dev-host` 必须先替换成真实 shared-dev 域名或网关地址，再继续校验。

默认会生成两份 `0600` 文件：

- 服务器侧：
  - `$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env`
- 操作机侧：
  - `$HOME/.config/yuantus/p2-shared-dev.env`

并会直接打印：

- `admin` 密码
- `ops-viewer` 密码
- 后续该执行的命令

如果你不想手工想密码，优先用这一步。

紧接着先校验两份 env：

```bash
scripts/validate_p2_shared_dev_env.sh
```

### 1. 服务器侧：准备 bootstrap env

```bash
scp "$HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env" \
  <user>@<server-host>:<server-repo>/deployments/docker/shared-dev.bootstrap.env
```

如果你没用 helper，也可以继续手工：

```bash
cp deployments/docker/shared-dev.bootstrap.env.example /tmp/shared-dev.bootstrap.env
```

然后至少修改：

- `YUANTUS_BOOTSTRAP_ADMIN_PASSWORD`
- `YUANTUS_BOOTSTRAP_VIEWER_PASSWORD`

通常保持默认即可：

- `YUANTUS_BOOTSTRAP_TENANT_ID=tenant-1`
- `YUANTUS_BOOTSTRAP_ORG_ID=org-1`
- `YUANTUS_BOOTSTRAP_ADMIN_USERNAME=admin`
- `YUANTUS_BOOTSTRAP_VIEWER_USERNAME=ops-viewer`
- `YUANTUS_BOOTSTRAP_DATASET_MODE=p2-observation`

如果不用 `scp`，也必须用等价的安全方式把最终 env 文件放到远端：

- `<server-repo>/deployments/docker/shared-dev.bootstrap.env`

### 2. 服务器侧：跑一次 bootstrap

```bash
cd <server-repo>
docker compose --env-file ./deployments/docker/shared-dev.bootstrap.env \
  --profile bootstrap run --rm bootstrap
```

预期：

- migrations 跑通
- `seed-identity admin`
- `seed-identity ops-viewer`
- `seed-meta`
- `seed_p2_observation_fixtures.py`
- 输出 fixture manifest 路径

### 3. 服务器侧：启动常驻服务

```bash
docker compose up -d api worker
```

### 4. 服务器侧：做最小存活检查

```bash
docker compose ps
curl -fsS http://127.0.0.1:7910/api/v1/health
```

如果地址不是本机回环，换成真实 shared-dev 域名或网关地址。

### 5. 操作机侧：创建 observation env

```bash
ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
mkdir -p "$(dirname "$ENV_FILE")"

cat > "$ENV_FILE" <<'ENVEOF'
BASE_URL="https://change-me-shared-dev-host"
USERNAME="admin"
PASSWORD="<same bootstrap admin password>"
TENANT_ID="tenant-1"
ORG_ID="org-1"
ENVIRONMENT="shared-dev"
ENVEOF

chmod 600 "$ENV_FILE"
```

如果第 0 步已经跑过，通常不需要再手工创建这份文件。

手工创建时，先校验：

```bash
scripts/validate_p2_shared_dev_env.sh --mode observation --observation-env "$ENV_FILE"
```

如果后面要单独补 `403` 分支 smoke，另记下：

- `ops-viewer`
- `<bootstrap viewer password>`

### 6. 操作机侧：先跑 precheck

```bash
scripts/precheck_p2_observation_regression.sh --env-file "$ENV_FILE"
```

预期：

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary_probe.json`

如果这一步不绿，不要继续 full regression。

### 7. 操作机侧：跑 canonical wrapper

仅在 precheck 通过后执行：

```bash
OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="$OUTPUT_DIR" ARCHIVE_RESULT=1 \
  scripts/run_p2_observation_regression.sh --env-file "$ENV_FILE"
```

### 8. 可选：补权限三态 smoke

这一段只在值班人明确允许时做：

- unauthenticated 预期 `401`
- `ops-viewer` 预期 `403`
- `admin` 预期 `200`

目标 ECO 使用 bootstrap manifest 里的：

- `eco-specialist`

## 预期业务结果

bootstrap 成功后，shared-dev 初始 observation 应能得到：

- baseline:
  - `pending=1`
  - `overdue=2`
  - `escalated=0`
- after one `escalate-overdue`:
  - `pending=1`
  - `overdue=3`
  - `escalated=1`
- permission tri-state on `eco-specialist`:
  - `401 / 403 / 200`

## 需要回传的结果

至少回传：

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary_probe.json`
- `summary.json`
- `items.json`
- `anomalies.json`
- `export.csv`
- `README.txt`
- `OBSERVATION_RESULT.md`

如果 wrapper 开了 `ARCHIVE_RESULT=1`，优先直接回传：

- `${OUTPUT_DIR}.tar.gz`

## 辅助脚本

可直接打印命令模板：

- `scripts/print_p2_shared_dev_bootstrap_commands.sh`
- `scripts/print_p2_shared_dev_observation_commands.sh`

前者负责 bootstrap 初始化；
后者负责 observation 回归执行。
