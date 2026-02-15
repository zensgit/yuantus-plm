# Dev Log (2026-02-15): verify_all DEDUP_CONFIG Print Order

## Context

`scripts/verify_all.sh` previously printed `DEDUP_CONFIG` before Dedup host-port auto-resolution.
That could show stale values (for example `DEDUP_VISION_PORT=<empty>`) even though preflight later resolved the port.

## Changes

1. Refactored Dedup config printing.

- Added helper: `print_dedup_config()`
- Keeps existing `DEDUP_CONFIG` content and effective URL calculation.

2. Changed output order in preflight.

- Dedup port is resolved first.
- Then `print_dedup_config` is called.

This guarantees printed effective URLs reflect runtime-resolved `DEDUP_VISION_PORT` /
`YUANTUS_DEDUP_VISION_FALLBACK_PORT`.

3. Added CI contract test.

- `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_dedup_config_order.py`
- Verifies `print_dedup_config` invocation appears after `Dedup port resolved` logging.

4. Wired into contracts list.

- `.github/workflows/ci.yml`

## Verification

Executed:

```bash
./.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_dedup_config_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_env_allowlist.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_health_http_code.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_is_truthy_order.py \
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

- `Dedup port resolved ...` appears before `DEDUP_CONFIG:`
- `DEDUP_CONFIG` shows resolved effective values
