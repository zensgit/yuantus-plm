# Verification - Full Regression (UI Aggregation + Config Variants)

- 时间：2026-01-29 13:22 +0800
- 命令：`RUN_UI_AGG=1 RUN_CONFIG_VARIANTS=1 scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：ALL TESTS PASSED (PASS=43, FAIL=0, SKIP=10)

## 摘要

包含 UI 聚合 + 配置变体扩展的全量回归全部通过。部分外部依赖场景按开关跳过。

```
PASS: 43  FAIL: 0  SKIP: 10
ALL TESTS PASSED
```
