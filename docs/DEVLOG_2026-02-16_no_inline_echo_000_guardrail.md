# Dev Log (2026-02-16): Guardrail for Inline `echo "000"` HTTP Fallback

## Context

After normalizing HTTP code handling in key CAD verification scripts, we added a
repository-level guardrail to prevent regressions from reintroducing:

```bash
... -w '%{http_code}' ... || echo "000"
```

This pattern can produce confusing `000000` output when curl already emits `000`.

## Changes

1. Added contract test:

- `src/yuantus/meta_engine/tests/test_ci_contracts_no_inline_echo_000_in_scripts.py`
- Scans `scripts/*.sh` and fails if it finds:
  - `|| echo "000"`
  - `|| echo '000'`

2. Wired test into CI contracts:

- `.github/workflows/ci.yml`

## Verification

Executed:

```bash
./.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_no_inline_echo_000_in_scripts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```

Result:

- `5 passed`

Contracts full set:

- `66 passed`
