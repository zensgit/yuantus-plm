# Release Notes v0.1.3 (Update 2026-02-01)

## Highlights

- P2 配置变型规则：VariantRule + Effective BOM + 配置实例缓存
- P3 制造：EBOM -> MBOM、MBOM 结构行项、Routing/Operation、工时/成本估算

## Details

### Config Variants (P2)
- 新增变型规则模型与 API（基于选项条件的 exclude）
- Effective BOM 按 selections 应用变型规则
- 新增配置实例并缓存有效 BOM
- 选择值校验（必填、类型、单选/多选）

### Manufacturing (P3)
- EBOM -> MBOM 转换（排除/替代/phantom 折叠）
- MBOM 行项持久化 + 结构读取 + EBOM/MBOM 对比
- Routing + Operation 管理，工时/成本计算与路由复制

## Verification

- Config 变型规则脚本：`scripts/verify_config_variant_rules.sh`（PASS）
- MBOM + Routing 脚本：`scripts/verify_manufacturing_mbom_routing.sh`（PASS）
- 汇总记录：`docs/VERIFICATION_RESULTS.md`（Run P2 / Run P3）
- 单测：`src/yuantus/meta_engine/tests/test_config_variants.py`、`src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py`
