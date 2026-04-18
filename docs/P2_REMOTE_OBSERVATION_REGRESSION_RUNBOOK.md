# P2 Remote Observation Regression Runbook

日期：2026-04-18

## 目标

这份 runbook 用于在当前冻结的远端观察面上重复执行一次最小 P2 observation 回归。

它的目标不是重建环境，也不是重新造一套 clean seed，而是：

- 确认 `yuantus-p2-api` 仍可用
- 重新采集 `summary / items / export / anomalies`
- 重渲染 `OBSERVATION_RESULT.md`
- 在需要时做一次最小 `escalate-overdue` 复核

## 当前观察面身份

- 主机：`142.171.239.56`
- 目录：`/home/mainuser/Yuantus-p2-mini`
- 容器：`yuantus-p2-api`
- 地址：`http://127.0.0.1:7910`
- 身份：临时远端 `local-dev-env`

这个环境已经冻结为回归观察面。

不要把它当成：

- shared-dev 正式基线
- 可反复演示正向 escalation 迁移的 clean seed 环境

## 当前冻结基线

当前冻结基线对应的已知结果是：

- `pending_count = 2`
- `overdue_count = 3`
- `escalated_count = 1`
- `total_anomalies = 2`
- `escalated_unresolved = 1`
- `overdue_not_escalated = 1`
- `no_candidates = 0`

这不是 clean local seed 的初始态，而是“已做过一次 auto-assign + 一次 escalation”后的稳定态。

## 前提

操作者需要：

- 可用 SSH：
  - `ssh -i ~/.ssh/metasheet2_deploy mainuser@142.171.239.56`
- 远端目录 `/home/mainuser/Yuantus-p2-mini` 仍在
- 容器 `yuantus-p2-api` 仍在运行
- 可使用 `admin / admin`

## 最小执行步骤

### 1. 登录远端并做存活检查

```bash
ssh -i ~/.ssh/metasheet2_deploy mainuser@142.171.239.56

cd /home/mainuser/Yuantus-p2-mini

docker ps --filter name=yuantus-p2-api --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -fsS http://127.0.0.1:7910/api/v1/health
```

如果这里失败，先不要继续采集，先看：

- `docker logs --tail 100 yuantus-p2-api`
- `docs/DEV_AND_VERIFICATION_REMOTE_DEPLOY_REMEDIATION_20260418.md`

### 2. 准备一个新的结果目录

不要覆盖已有：

- `/home/mainuser/Yuantus-p2-mini/local-dev-env/results`
- `/home/mainuser/Yuantus-p2-mini/remote-dev-results/round1-before`
- `/home/mainuser/Yuantus-p2-mini/remote-dev-results/round1-after`

建议每次新建一个带时间戳的目录：

```bash
TS=$(date +%Y%m%d-%H%M%S)
OUT="/home/mainuser/Yuantus-p2-mini/remote-dev-results/${TS}-baseline"
mkdir -p "$OUT"
```

### 3. 获取 admin token

`verify_p2_dev_observation_startup.sh` 不负责登录，必须先拿 token。

```bash
ADMIN_TOKEN=$(curl -sS -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"admin","password":"admin","org_id":"org-1"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

如果要额外复核一次权限拒绝，再拿 `ops-viewer` token：

```bash
VIEWER_TOKEN=$(curl -sS -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-1","username":"ops-viewer","password":"ops123","org_id":"org-1"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

### 4. 采集只读 baseline

```bash
BASE_URL=http://127.0.0.1:7910 \
TOKEN="$ADMIN_TOKEN" \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
OUTPUT_DIR="$OUT" \
bash scripts/verify_p2_dev_observation_startup.sh
```

预期：

- `summary / items / export / anomalies` 全部返回 `200`
- 结果写入 `$OUT`

### 5. 渲染结果

优先直接在容器里跑 renderer，避免依赖远端宿主机 Python 环境。

```bash
docker exec -w /work yuantus-p2-api \
  python scripts/render_p2_observation_result.py \
  "/work/remote-dev-results/$(basename "$OUT")" \
  --operator mainuser \
  --environment remote-local-dev-env
```

查看结果：

```bash
sed -n '1,220p' "$OUT/OBSERVATION_RESULT.md"
```

### 6. 只判断这一份结果

优先只看：

- `OBSERVATION_RESULT.md`

判断三件事：

- 是否稳定
- 是否有异常
- 是否仍与当前冻结基线一致

当前冻结环境里，通常应看到：

- `pending_count = 2`
- `overdue_count = 3`
- `escalated_count = 1`
- `escalated_unresolved = 1`
- `overdue_not_escalated = 1`
- `no_candidates = 0`

## 可选：最小状态复核

这一段是可选的，不建议混进日常只读回归。

### 1. 再打一发 `escalate-overdue`

```bash
AFTER="/home/mainuser/Yuantus-p2-mini/remote-dev-results/${TS}-after"
mkdir -p "$AFTER"

curl -sS -X POST http://127.0.0.1:7910/api/v1/eco/approvals/escalate-overdue \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' \
  -H 'x-org-id: org-1' \
  -o "$AFTER/escalate-response.json"

cat "$AFTER/escalate-response.json"
```

在当前冻结环境里，预期是：

```json
{"escalated":0,"items":[]}
```

### 2. 再采一轮并重渲染

```bash
BASE_URL=http://127.0.0.1:7910 \
TOKEN="$ADMIN_TOKEN" \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
OUTPUT_DIR="$AFTER" \
bash scripts/verify_p2_dev_observation_startup.sh

docker exec -w /work yuantus-p2-api \
  python scripts/render_p2_observation_result.py \
  "/work/remote-dev-results/$(basename "$AFTER")" \
  --operator mainuser \
  --environment remote-local-dev-env
```

### 3. 结果判定

当前冻结环境里，`round before` 和 `round after` 应基本不变。

原因是：

- 剩余的 `overdue_not_escalated` 样本是 `eco-overdue-admin`
- 它已落在已知 idempotent guard 路径上
- 因此再次 `escalate-overdue` 不会产生新的正向迁移

## 可选：权限拒绝快速复核

如果只想补一轮 `403 / 200` 语义复核，可单独执行，不要和 frozen baseline 比对混在一起。

```bash
curl -sS -X POST "http://127.0.0.1:7910/api/v1/eco/<eco-specialist-id>/auto-assign-approvers" \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H 'x-tenant-id: tenant-1' \
  -H 'x-org-id: org-1'

curl -sS -X POST "http://127.0.0.1:7910/api/v1/eco/<eco-specialist-id>/auto-assign-approvers" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'x-tenant-id: tenant-1' \
  -H 'x-org-id: org-1'
```

预期：

- `ops-viewer` 返回 `403`
- `admin` 返回 `200`

## 不要做的事

在当前冻结回归观察面上，不要直接做下面这些动作：

- 不要 `rebuild`
- 不要 `reseed`
- 不要再跑 `local-dev-env/start.sh`
- 不要覆盖现有 `round1-before / round1-after`
- 不要把这套环境误记为 shared-dev 正式基线

## 如果你需要新的正向状态迁移

如果你的目标是再次证明：

- `overdue_not_escalated -> escalated_unresolved`

那就不要继续使用当前冻结环境。

应当：

1. 明确新建一套可重置环境
2. 重新 seed/rebuild
3. 再做正向 write-path 演示

参考：

- `docs/DEV_AND_VERIFICATION_REMOTE_DEPLOY_REMEDIATION_20260418.md`
- `docs/DEV_AND_VERIFICATION_P2_REMOTE_OBSERVATION_VALIDATION_20260418.md`

## 最小回看产物

至少回看：

- `OBSERVATION_RESULT.md`
- `summary.json`
- `items.json`
- `anomalies.json`
- `export.csv`

如果脚本失败，优先看输出目录里的响应体，再看：

```bash
docker logs --tail 100 yuantus-p2-api
```
