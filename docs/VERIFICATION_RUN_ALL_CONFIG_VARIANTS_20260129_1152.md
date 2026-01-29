# Verification - Full Regression (Config Variants Enabled)

- 时间：2026-01-29 11:52 +0800
- 命令：`RUN_CONFIG_VARIANTS=1 scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：ALL TESTS PASSED (PASS=37, FAIL=0, SKIP=16)

## 摘要

本次全量回归包含 S12 Config Variants 扩展逻辑验证，所有必测项通过，部分 CAD/外部依赖场景按开关跳过。

```
PASS: 37  FAIL: 0  SKIP: 16
ALL TESTS PASSED
```
