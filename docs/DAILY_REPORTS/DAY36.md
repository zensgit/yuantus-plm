# Day 36 - Key-Value Weight Parsing

## Scope
- Parse numeric weight from key-value fields with units (e.g. 1.2kg).
- Update local CAD extraction verification to assert parsed weight.

## Verification - CAD Extract Local

Command:

```bash
bash scripts/verify_cad_extract_local.sh
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Weight parsed from `1.2kg` → `1.2`
