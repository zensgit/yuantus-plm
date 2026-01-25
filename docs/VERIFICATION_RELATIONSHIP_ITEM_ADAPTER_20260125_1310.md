# Relationship Item Adapter Verification (2026-01-25 13:10 +0800)

## 验证范围

- Relationship 解析优先 ItemType.is_relationship（RelationshipType 仅作为 legacy fallback）
- Query expand 路径优先 ItemType 关系

## 执行命令

```bash
bash scripts/verify_run_h.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_RUN_H_20260125_1310.log
```

## 结果摘要

- ALL CHECKS PASSED

## 日志

- `docs/VERIFY_RUN_H_20260125_1310.log`
