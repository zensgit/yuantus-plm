# Dev Log (2026-02-16): CAD Script HTTP Code Normalization

## Context

Several CAD verification scripts used:

```bash
curl ... -w '%{http_code}' ... || echo "000"
```

When curl failed hard, this could produce `000000` in logs (`%{http_code}` emits `000`, fallback adds another `000`).

## Changes

1. Normalized HTTP code handling in CAD scripts

- `scripts/verify_cad_preview_2d.sh`
- `scripts/verify_cad_ocr_titleblock.sh`
- `scripts/verify_docdoku_alignment.sh`
- `scripts/verify_cad_real_samples.sh`

Each script now:

- defines `normalize_http_code()`
- captures curl output with `|| true`
- normalizes to strict 3-digit code (`000` fallback when invalid)
- avoids inline `|| echo "000"`

2. CI contract coverage

- Added:
  - `src/yuantus/meta_engine/tests/test_ci_contracts_http_code_normalization_cad_scripts.py`
- Updated:
  - `.github/workflows/ci.yml` contract test list

## Verification

Contracts:

```bash
./.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_http_code_normalization_cad_scripts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```

Result:

- `5 passed`

CI contracts full set:

- `65 passed`

Runtime smoke (CAD ML unreachable):

```bash
CAD_ML_BASE_URL=http://127.0.0.1:9 bash scripts/verify_cad_ocr_titleblock.sh
CAD_ML_BASE_URL=http://127.0.0.1:9 CAD_PREVIEW_ALLOW_FALLBACK=0 bash scripts/verify_cad_preview_2d.sh
CAD_ML_BASE_URL=http://127.0.0.1:9 CAD_PREVIEW_ALLOW_FALLBACK=0 bash scripts/verify_docdoku_alignment.sh
```

Observed:

- all scripts report `HTTP 000` (no `000000`)
