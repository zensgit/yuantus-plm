# 全量回归验证（含 S12 Config Variants）

- 时间：2026-01-28 23:18 +0800
- 基地址：`http://127.0.0.1:7910`
- 命令：`RUN_CONFIG_VARIANTS=1 bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1`
- 结果：`ALL TESTS PASSED`
- 汇总：`PASS=37, FAIL=0, SKIP=16`
- 日志：`/tmp/verify_all_s12_20260128_2318.log`

## 关键结果

- S12 (Config Variants)：PASS
- 其他核心模块：Run H / S1 / S2 / S3.x / S4 / BOM Compare / Baseline / Version-File Binding 均 PASS
- 跳过项：与外部依赖或可选开关相关（CAD 实样 / UI 聚合 / Tenant Provisioning 等）

## 摘要输出

```text
PASS: 37  FAIL: 0  SKIP: 16
ALL TESTS PASSED
```
