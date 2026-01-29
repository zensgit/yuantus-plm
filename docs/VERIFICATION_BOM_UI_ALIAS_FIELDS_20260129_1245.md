# Verification - BOM UI Alias Fields

- 时间：2026-01-29 12:45 +0800
- 结果：ALL CHECKS PASSED

## 命令

```bash
bash scripts/verify_bom_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

## 校验点

- where-used 返回 `parent_number/child_number` 别名
- bom_compare 返回 `child_number` 别名
- substitutes 返回 `substitute_number`

```
ALL CHECKS PASSED
```
