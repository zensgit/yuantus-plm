# P2 Shared Dev Observation Handoff

日期：2026-04-17

## 目标

这份 handoff 用于把 `P2` 观察期 startup smoke 交给持有共享 dev 环境访问权限的操作者执行。

适用场景：

- 有真实共享 `dev` 环境
- 有有效 `BASE_URL`
- 有可用 `JWT`，或可安全提供一次性账号密码
- 已知 `TENANT_ID / ORG_ID`

不适用场景：

- 没有共享 dev 凭证
- 只想做本地 smoke

## 前提

操作者需要准备：

- `BASE_URL`
- `TOKEN`，或 `USERNAME / PASSWORD`
- `TENANT_ID`
- `ORG_ID`

不要把长期凭证直接写进仓库。
如果落 env 文件，放在仓库外，例如：`$HOME/.config/yuantus/p2-shared-dev.env`，并设置为 `0600`。

## 最小执行步骤

### 1. 首选：准备本地 env 文件

```bash
ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
mkdir -p "$(dirname "$ENV_FILE")"

cat > "$ENV_FILE" <<'ENVEOF'
BASE_URL="http://<dev-host>"
TOKEN="<jwt>"
TENANT_ID="<tenant>"
ORG_ID="<org>"
ENVIRONMENT="shared-dev"
ENVEOF

chmod 600 "$ENV_FILE"
```

### 2. 执行本地 precheck

```bash
scripts/precheck_p2_observation_regression.sh --env-file "$ENV_FILE"
```

预期产物：

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`

如果这一步不绿，不要继续 full observation。

### 3. 执行 canonical shell wrapper

```bash
OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="$OUTPUT_DIR" ARCHIVE_RESULT=1 \
  scripts/run_p2_observation_regression.sh --env-file "$ENV_FILE"
```

如果没有现成 `JWT`，可改用 wrapper 自带登录：

```bash
ENV_FILE="$HOME/.config/yuantus/p2-shared-dev.env"
mkdir -p "$(dirname "$ENV_FILE")"

cat > "$ENV_FILE" <<'ENVEOF'
BASE_URL="http://<dev-host>"
USERNAME="<user>"
PASSWORD="<password>"
TENANT_ID="<tenant>"
ORG_ID="<org>"
ENVIRONMENT="shared-dev"
ENVEOF

chmod 600 "$ENV_FILE"

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="$OUTPUT_DIR" ARCHIVE_RESULT=1 \
  scripts/run_p2_observation_regression.sh --env-file "$ENV_FILE"
```

如果你不想落 env 文件，也可以继续沿用直接导出环境变量方式：

```bash
export BASE_URL="http://<dev-host>"
export TOKEN="<jwt>"
export TENANT_ID="<tenant>"
export ORG_ID="<org>"

scripts/precheck_p2_observation_regression.sh

OUTPUT_DIR="./tmp/p2-shared-dev-observation-$(date +%Y%m%d-%H%M%S)"
BASE_URL="$BASE_URL" \
TOKEN="$TOKEN" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
ENVIRONMENT="shared-dev" \
ARCHIVE_RESULT=1 \
OUTPUT_DIR="$OUTPUT_DIR" \
scripts/run_p2_observation_regression.sh
```

### 4. 打包证据

如果上面用了 `ARCHIVE_RESULT=1`，wrapper 会自动生成：

```bash
${OUTPUT_DIR}.tar.gz
```

否则手工打包：

```bash
tar -czf "${OUTPUT_DIR}.tar.gz" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"
```

## 需要回传的结果

至少回传：

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary.json`
- `items.json`
- `anomalies.json`
- `export.csv`
- `README.txt`
- `OBSERVATION_RESULT.md`

如果可以，直接回传整个：

- `${OUTPUT_DIR}.tar.gz`

## 可选 write smoke

只有在值班人明确允许时才执行：

```bash
BASE_URL="$BASE_URL" \
TOKEN="$TOKEN" \
TENANT_ID="$TENANT_ID" \
ORG_ID="$ORG_ID" \
RUN_WRITE_SMOKE=1 \
AUTO_ASSIGN_ECO_ID="<eco-id>" \
OUTPUT_DIR="$OUTPUT_DIR-write" \
scripts/verify_p2_dev_observation_startup.sh
```

## 回传后如何处理

回传产物后，由审阅方：

1. 审 `summary / items / anomalies` 是否一致
2. 检查 `export.csv` 是否和 dashboard 口径一致
3. 判断是否需要：
   - 补 observation template
   - 开一条 docs-only baseline 记录
   - 进入异常处理/升级流程

## 辅助脚本

可直接运行：

- `scripts/print_p2_shared_dev_observation_commands.sh`
- `scripts/run_p2_observation_regression_workflow.sh`

前者用于打印 shell 执行命令；后者用于本地直接触发 GitHub Actions workflow。
