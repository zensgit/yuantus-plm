#!/usr/bin/env python3

import argparse
import json
from datetime import datetime
from pathlib import Path


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Error reading artifact {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing JSON artifact {path}: {exc}") from exc


def summarize_items(items):
    total = len(items)
    pending = sum(1 for item in items if not item.get("is_overdue"))
    overdue = sum(1 for item in items if item.get("is_overdue"))
    return total, pending, overdue


def format_json_block(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_markdown(result_dir: Path, summary: dict, items: list, anomalies: dict, operator: str, environment: str):
    total_items, pending_items, overdue_items = summarize_items(items)
    total_anomalies = anomalies.get("total_anomalies", 0)
    no_candidates = len(anomalies.get("no_candidates", []))
    escalated_unresolved = len(anomalies.get("escalated_unresolved", []))
    overdue_not_escalated = len(anomalies.get("overdue_not_escalated", []))

    no_candidates_status = (
        "⚠️ 未命中（环境中可能存在 active superuser bypass）"
        if no_candidates == 0
        else "✅ 已命中"
    )

    return f"""# P2 Observation Result

日期：{datetime.now().date().isoformat()}
执行人：{operator}
环境：{environment}

## 1. 输出目录

- `{result_dir}`

## 2. Dashboard / Audit 基线结果

### 2.1 summary

```json
{format_json_block(summary)}
```

### 2.2 items

- 总条数：{total_items}
- `pending` 条数：{pending_items}
- `overdue` 条数：{overdue_items}

### 2.3 anomalies

- `total_anomalies`：{total_anomalies}
- `no_candidates`：{no_candidates}
- `escalated_unresolved`：{escalated_unresolved}
- `overdue_not_escalated`：{overdue_not_escalated}

## 3. 验收结论

| 目标 | 状态 | 证据 |
|---|---|---|
| `summary` 不再全 0 | {"✅" if any(summary.get(key, 0) for key in ("pending_count", "overdue_count", "escalated_count")) else "❌"} | `pending_count={summary.get("pending_count", 0)}`, `overdue_count={summary.get("overdue_count", 0)}`, `escalated_count={summary.get("escalated_count", 0)}` |
| `anomalies` 有真实记录 | {"✅" if total_anomalies > 0 else "❌"} | `total_anomalies={total_anomalies}` |
| 能区分 `pending / overdue` | {"✅" if pending_items > 0 and overdue_items > 0 else "⚠️"} | `pending_items={pending_items}`, `overdue_items={overdue_items}` |
| `no_candidates` 是否命中 | {no_candidates_status} | `no_candidates={no_candidates}` |

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
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render a Markdown observation summary from a P2 observation artifact directory."
    )
    parser.add_argument(
        "result_dir",
        help="Artifact directory produced by scripts/verify_p2_dev_observation_startup.sh",
    )
    parser.add_argument(
        "--output",
        help="Output markdown path. Default: <result_dir>/OBSERVATION_RESULT.md",
    )
    parser.add_argument("--operator", default="____", help="Operator name to record")
    parser.add_argument("--environment", default="____", help="Environment label to record")
    return parser.parse_args()


def main():
    args = parse_args()
    result_dir = Path(args.result_dir).resolve()
    summary_path = result_dir / "summary.json"
    items_path = result_dir / "items.json"
    anomalies_path = result_dir / "anomalies.json"

    for path in (summary_path, items_path, anomalies_path):
        if not path.is_file():
            raise SystemExit(f"Missing required artifact: {path}")

    output_path = Path(args.output).resolve() if args.output else result_dir / "OBSERVATION_RESULT.md"
    markdown = render_markdown(
        result_dir=result_dir,
        summary=load_json(summary_path),
        items=load_json(items_path),
        anomalies=load_json(anomalies_path),
        operator=args.operator,
        environment=args.environment,
    )
    output_path.write_text(markdown, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
