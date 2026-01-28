# S12 Configuration/Variant BOM 验证记录（2026-01-28 23:03）

- 验证时间：2026-01-28 23:03 +0800
- 基地址：`http://127.0.0.1:7910`
- 租户/组织：`tenant-1` / `org-1`
- 验证脚本：`scripts/verify_config_variants.sh`
- 结果：`ALL CHECKS PASSED`

## 执行命令

```bash
bash scripts/verify_config_variants.sh http://127.0.0.1:7910 tenant-1 org-1
```

## 验证要点

- 创建配置选项集与选项（Color/Voltage）。
- 创建父子件与 BOM 行，并设置 `config_condition`。
- `config` 匹配时返回子件；不匹配时返回 0；不带 config 时默认返回 1。

## 输出摘要

```text
ALL CHECKS PASSED
```
