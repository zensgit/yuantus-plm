# YuantusPLM v0.1.3 发布公告（更新 2026-02-01）

## 发布摘要

- 版本：v0.1.3（更新）
- 日期：2026-02-01
- 重点：配置变型规则（P2）+ 制造 MBOM/Routing（P3）

## 本次亮点

- 配置变型：VariantRule、Effective BOM、配置实例缓存与选择校验
- 制造：EBOM -> MBOM、MBOM 行项、Routing/Operation、工时与成本估算
- 验证脚本与单测补齐

## 验证与文档

- Release Notes：`docs/RELEASE_NOTES_v0.1.3_update_20260201.md`
- Changelog：`CHANGELOG.md`
- 验证汇总：`docs/VERIFICATION_RESULTS.md`
- 验证脚本：
  - `scripts/verify_config_variant_rules.sh`
  - `scripts/verify_manufacturing_mbom_routing.sh`

## 快速验证

```bash
bash scripts/verify_config_variant_rules.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_manufacturing_mbom_routing.sh http://127.0.0.1:7910 tenant-1 org-1
```
