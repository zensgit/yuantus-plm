# P2 Observation Result

日期：2026-04-19
执行人：chouhua
环境：shared-dev

## 1. 输出目录

- `/Users/chouhua/Downloads/Github/Yuantus/tmp/p2-shared-dev-observation-20260419-193242`

## 2. Dashboard / Audit 基线结果

### 2.1 summary

```json
{
  "pending_count": 2,
  "overdue_count": 3,
  "escalated_count": 1,
  "by_stage": [
    {
      "stage_id": "5da342a5-dca1-4323-9bb9-3bf57feeace1",
      "stage_name": "Review",
      "pending": 1,
      "overdue": 3
    },
    {
      "stage_id": "a25835de-22d2-41af-a175-90437d3d8d1a",
      "stage_name": "SpecialistReview",
      "pending": 1,
      "overdue": 0
    }
  ],
  "by_role": [
    {
      "role": "engineer",
      "count": 4
    },
    {
      "role": "specialist",
      "count": 1
    }
  ],
  "by_assignee": [
    {
      "user_id": 1,
      "username": "admin",
      "pending_count": 4
    },
    {
      "user_id": 2,
      "username": "ops-viewer",
      "pending_count": 1
    }
  ]
}
```

### 2.2 items

- 总条数：5
- `pending` 条数：2
- `overdue` 条数：3

### 2.3 anomalies

- `total_anomalies`：2
- `no_candidates`：0
- `escalated_unresolved`：1
- `overdue_not_escalated`：1

## 3. 验收结论

| 目标 | 状态 | 证据 |
|---|---|---|
| `summary` 不再全 0 | ✅ | `pending_count=2`, `overdue_count=3`, `escalated_count=1` |
| `anomalies` 有真实记录 | ✅ | `total_anomalies=2` |
| 能区分 `pending / overdue` | ✅ | `pending_items=2`, `overdue_items=3` |
| `no_candidates` 是否命中 | ⚠️ 未命中（环境中可能存在 active superuser bypass） | `no_candidates=0` |

## 4. 特殊说明

- 如果环境中存在 active superuser bypass，`no_candidates` 可能长期保持 `0`
- 这种情况下，RBAC 缺口应结合 `overdue_not_escalated` 和 auto-assign 明确失败信号判断

## 5. 产物清单

- `summary.json`
- `items.json`
- `export.csv`
- `export.json`
- `anomalies.json`
- `README.txt`
