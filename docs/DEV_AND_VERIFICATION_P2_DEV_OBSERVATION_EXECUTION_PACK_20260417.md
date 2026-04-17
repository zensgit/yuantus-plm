# P2 Dev Observation Execution Pack

日期：2026-04-17

## 目标

把 `P2_DEV_OBSERVATION_STARTUP_CHECKLIST` 第 2 到第 6 步从纯文档动作收成可直接执行的启动脚本，方便在开发环境里做真实运营观察前的基线采集。

本次不新增审批功能，不伪造真实 dev 环境结果；只补“执行包”。

## 交付

新增：

- `scripts/verify_p2_dev_observation_startup.sh`

更新：

- `docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md`
- `docs/P2_OPS_RUNBOOK.md`

## 脚本能力

`verify_p2_dev_observation_startup.sh` 提供：

1. 读取 `BASE_URL` 和 `TOKEN`
2. 采集只读基线证据：
   - `dashboard/summary`
   - `dashboard/items`
   - `dashboard/export?fmt=json`
   - `dashboard/export?fmt=csv`
   - `audit/anomalies`
3. 可选执行 write smoke：
   - `POST /eco/{eco_id}/auto-assign-approvers`
   - `POST /eco/approvals/escalate-overdue`
4. 将结果写入带时间戳的 `OUTPUT_DIR`
5. 生成简单 `README.txt`，方便把结果附到观察模板

## 运行方式

只读基线：

```bash
BASE_URL=http://localhost:8000 \
TOKEN=your-jwt-token-here \
scripts/verify_p2_dev_observation_startup.sh
```

带 write smoke：

```bash
BASE_URL=http://localhost:8000 \
TOKEN=your-jwt-token-here \
RUN_WRITE_SMOKE=1 \
AUTO_ASSIGN_ECO_ID=eco-123 \
scripts/verify_p2_dev_observation_startup.sh
```

## 验证

### 1. Shell syntax

```bash
bash -n scripts/verify_p2_dev_observation_startup.sh
```

结果：

- 通过

### 2. Help smoke

```bash
scripts/verify_p2_dev_observation_startup.sh --help
```

结果：

- 返回 usage

### 3. Doc index contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py
```

结果：

- 预期通过

## 结论

- 观察期启动 checklist 现在有了可执行入口
- 真实 dev 环境 smoke 仍需要由值班人提供 `BASE_URL/TOKEN` 后执行
- 本次交付属于执行工具和文档增强，不改变审批链运行时语义
