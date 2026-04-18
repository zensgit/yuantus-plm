# P2 One-Page Dev Guide

**适用范围**：开发阶段 / shared dev 观察前后  
**目标**：不要翻整套文档，只用这一页完成执行与判断

---

## 1. 你平时只需要看什么

日常只看这 3 个文件：

- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md`
- `docs/P2_OPS_RUNBOOK.md`

其余 `DEV_AND_VERIFICATION_*` 文档默认都当归档，不需要日常阅读。

---

## 2. 你真正要跑的命令

### 2.1 采集观察结果

```bash
BASE_URL=http://<dev-host> \
TOKEN=<jwt> \
TENANT_ID=<tenant> \
ORG_ID=<org> \
OUTPUT_DIR=./tmp/p2-observation-shared-dev-$(date +%Y%m%d-%H%M%S) \
scripts/verify_p2_dev_observation_startup.sh
```

### 2.2 固化成 Markdown 结果

```bash
python3 scripts/render_p2_observation_result.py \
  "$OUTPUT_DIR" \
  --operator "<name>" \
  --environment "shared-dev"
```

---

## 3. 你只需要看什么结果

优先只看：

- `$OUTPUT_DIR/OBSERVATION_RESULT.md`

不要先钻：

- `summary.json`
- `items.json`
- `anomalies.json`
- `export.csv`

只有在 `OBSERVATION_RESULT.md` 显示异常时，再回头看原始产物。

---

## 4. 你只需要做什么判断

当前阶段**不是**决定 `P2-4`，只做这 3 个判断：

1. 这轮 shared dev 观察是否正常跑通
2. 有没有明显异常
3. 是否需要继续观察或人工介入

---

## 5. 什么叫“正常”

至少满足：

- `summary/items/export/anomalies` 都返回成功
- 生成了 `OBSERVATION_RESULT.md`
- `OBSERVATION_RESULT.md` 里能看懂：
  - `pending`
  - `overdue`
  - `anomalies`

---

## 6. 什么异常最值得看

优先只看这 3 类：

- `overdue_not_escalated`
- `escalated_unresolved`
- `auto-assign` 明确失败

补充：

- `no_candidates` 在有 active `superuser` 的环境里可能长期为 `0`
- 这不一定是 bug，也不单独算观察失败

---

## 7. 什么时候再找 Codex

出现下面任一情况再回传结果：

- `OBSERVATION_RESULT.md` 显示异常数明显增加
- `overdue` 和 `escalated` 的变化对不上
- `auto-assign` 返回值和 audit/dashboards 对不上
- 你不确定这轮结果该归因于数据、权限还是代码

回传时最少给：

- `OBSERVATION_RESULT.md`
- `summary.json`
- `anomalies.json`
- `README.txt`

---

## 8. 当前不做什么

- 不再补本地轮次
- 不再造 local seed 样本
- 不启动 `P2-4`
- 不做 `BOM Diff / CAD Viewer / ECM sunset`

开发阶段现在的目标只有一个：  
**把 shared dev 观察跑通并留痕。**
