# Verification: BOM Obsolete Handling + Weight Rollup (2026-02-04)

## Environment

- Base URL: `http://127.0.0.1:7910`
- Tenant/Org: `tenant-1` / `org-1`

## 1) BOM Obsolete Script

```bash
bash scripts/verify_bom_obsolete.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result: **PASS**

## 2) BOM Weight Rollup Script

```bash
bash scripts/verify_bom_weight_rollup.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result: **PASS**

## 3) Playwright API Tests

```bash
npx playwright test playwright/tests/bom_obsolete_weight.spec.js
```

Result: **PASS**
