# Day 41 - CAD Attribute Normalization

## Scope
- Normalize material/weight/revision and ensure drawing_no fallback.

## Verification - CAD Attribute Normalization

Command:

```bash
bash scripts/verify_cad_attribute_normalization.sh
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- material: Stainless Steel 304
- weight: 1200g → 1.2kg
- revision: REV-A → A
