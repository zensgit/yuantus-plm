# Dev Log (2026-02-15): verify_all API Health HTTP Code Normalization

## Context

`scripts/verify_all.sh` used:

```bash
curl ... -w '%{http_code}' ... || echo "000"
```

When curl failed hard, this pattern could produce `000000` (`curl`-formatted `000` + fallback `000`), which is noisy and can confuse diagnostics.

## Changes

1. Added helper function in `scripts/verify_all.sh`:

- `api_health_http_code()`
- Executes the health probe and normalizes output to a strict 3-digit code.
- Falls back to `000` when output is not a valid 3-digit HTTP code.

2. Updated preflight health retry loop:

- Replaced inline curl expression with:
  - `HTTP_CODE="$(api_health_http_code)"`

3. Added CI contract test:

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_health_http_code.py`
- Verifies:
  - helper exists
  - 3-digit normalization guard exists
  - retry loop uses helper
  - legacy inline `|| echo "000"` pattern is absent

4. Wired test into CI contracts list:

- `.github/workflows/ci.yml`

## Verification

Executed:

```bash
./.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_health_http_code.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_is_truthy_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_env_allowlist.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```

Expected:

- all pass

Runtime smoke:

```bash
RUN_DEDUP=1 bash scripts/verify_all.sh http://127.0.0.1:9
```

Expected:

- preflight prints `HTTP 000` style code (no duplicated `000000`)
- no `command not found` related to helper calls
