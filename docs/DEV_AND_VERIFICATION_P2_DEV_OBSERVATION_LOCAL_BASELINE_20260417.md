# P2 Dev Observation Local Baseline

日期：2026-04-17

## 目标

在本地开发环境完成一次真实的 `P2` 观察期启动基线采集，而不是只停留在脚本 `--help` 或 TestClient smoke。

## 环境

本次使用本地临时启动的 API：

- `BASE_URL`: `http://127.0.0.1:7910`
- `tenant_id`: `tenant-1`
- `org_id`: `org-1`
- 数据配置：`.env` 中的 `YUANTUS_DATABASE_URL=sqlite:///yuantus_mt_skip.db`
- tenancy mode：`db-per-tenant-org`

启动步骤：

1. `PYTHONPATH=src .venv/bin/python -m yuantus.cli seed-identity --tenant tenant-1 --org org-1 --username admin --password admin --user-id 1 --roles admin`
2. `PYTHONPATH=src .venv/bin/python -m uvicorn yuantus.api.app:app --host 127.0.0.1 --port 7910`
3. `POST /api/v1/auth/login` 获取本地 token
4. 执行 `scripts/verify_p2_dev_observation_startup.sh`

## 运行命令

```bash
TOKEN=$(python3 - <<'PY'
import json
obj=json.load(open('tmp/p2-dev-observation-live/login.json'))
print(obj['access_token'])
PY
)

BASE_URL=http://127.0.0.1:7910 \
TOKEN="$TOKEN" \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
OUTPUT_DIR=tmp/p2-dev-observation-live/artifacts \
scripts/verify_p2_dev_observation_startup.sh
```

## 结果

真实 read-baseline smoke 全部通过：

- `GET /api/v1/eco/approvals/dashboard/summary` -> `200`
- `GET /api/v1/eco/approvals/dashboard/items` -> `200`
- `GET /api/v1/eco/approvals/dashboard/export?fmt=json` -> `200`
- `GET /api/v1/eco/approvals/dashboard/export?fmt=csv` -> `200`
- `GET /api/v1/eco/approvals/audit/anomalies` -> `200`

write smoke 本次未启用：

- `RUN_WRITE_SMOKE=0`

## 基线采样

### summary

```json
{
  "pending_count": 0,
  "overdue_count": 0,
  "escalated_count": 0,
  "by_stage": [],
  "by_role": [],
  "by_assignee": []
}
```

### items

- `[]`

### export.csv

- 仅 header

### anomalies

- `total_anomalies = 19`
- 全部来自 `overdue_not_escalated`
- `no_candidates = []`
- `escalated_unresolved = []`

这说明当前本地 dev 数据里已经存在一批历史 overdue ECO，但尚未触发 escalation。

## 产物

保存在：

- `tmp/p2-dev-observation-live/artifacts/summary.json`
- `tmp/p2-dev-observation-live/artifacts/items.json`
- `tmp/p2-dev-observation-live/artifacts/export.json`
- `tmp/p2-dev-observation-live/artifacts/export.csv`
- `tmp/p2-dev-observation-live/artifacts/anomalies.json`
- `tmp/p2-dev-observation-live/artifacts/README.txt`

## 结论

- `P2` 观察期启动脚本已在真实本地 dev 环境跑通
- 当前环境需要显式传入：
  - `TENANT_ID`
  - `ORG_ID`
- 当前本地基线不是“完全干净”，而是：
  - dashboard 为空
  - anomaly audit 已经识别出 `19` 条 `overdue_not_escalated`

这份结果足以作为开发环境观察期的第一条真实基线记录。
