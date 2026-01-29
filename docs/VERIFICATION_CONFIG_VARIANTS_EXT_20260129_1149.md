# Verification - Config Variant BOM (Extended)

- 时间：2026-01-29 11:49 +0800
- 范围：S12 配置变体条件表达增强
- 结果：ALL CHECKS PASSED

## 环境

- 本地启动（避免与 docker 7910 端口冲突）
- 端口：`7911`
- 环境变量：
  - `YUANTUS_AUTH_MODE=required`
  - `YUANTUS_SCHEMA_MODE=empty`
  - `YUANTUS_DATABASE_URL=sqlite:///yuantus_config_variants.db`
  - `YUANTUS_IDENTITY_DATABASE_URL=sqlite:///yuantus_config_variants_identity.db`

## 执行命令

```bash
env YUANTUS_DATABASE_URL=sqlite:///yuantus_config_variants.db \
    YUANTUS_IDENTITY_DATABASE_URL=sqlite:///yuantus_config_variants_identity.db \
    bash scripts/verify_config_variants.sh http://127.0.0.1:7911 tenant-1 org-1
```

## 验证要点

- 支持 `op` 运算符：`gte` / `ne` / `contains`
- `exists` / `missing` 条件
- 简写表达式：`Voltage>=200;Color=Red`
- 匹配/不匹配配置的 BOM 行过滤

## 结果

```
ALL CHECKS PASSED
```
