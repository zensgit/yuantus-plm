# P2 Observation Evaluation

- mode: `current-only`
- current: `./artifacts/p2-observation/shared-dev-142-readonly-20260421`

## Overall

- verdict: PASS
- checks: 5/5 passed

## Check Results

| Scope | Check | Status | Detail |
|---|---|---|---|
| `current` | items/export row count consistency | PASS | items_count=4, export_json_count=4, export_csv_rows=4 |
| `current` | summary matches items for pending_count | PASS | summary=0, derived=0 |
| `current` | summary matches items for overdue_count | PASS | summary=4, derived=4 |
| `current` | summary matches items for escalated_count | PASS | summary=1, derived=1 |
| `current` | anomaly total matches category counts | PASS | total_anomalies=3, derived_total=3 |
