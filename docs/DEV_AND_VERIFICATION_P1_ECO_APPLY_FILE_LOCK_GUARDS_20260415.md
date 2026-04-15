# P1 ECO Apply File Lock Guards

Date: 2026-04-15

## Scope
- Guard `ECOService.action_apply(...)` against foreign version checkouts and foreign file locks on the current/target versions.
- Keep `/apply-diagnostics` in parity with runtime `action_apply(...)` by surfacing the same lock blockers as structured validation issues.

## Changes
- `src/yuantus/meta_engine/services/release_validation.py`
  - Added `eco.version_locks_clear` to the default `eco_apply` ruleset.
- `src/yuantus/meta_engine/services/eco_service.py`
  - Added shared apply-time version/file lock inspection helper.
  - `get_apply_diagnostics(...)` now reports version/file lock blockers.
  - `action_apply(...)` now rejects foreign version checkout and foreign file locks before switching current version or projecting `ItemFile`.
- Tests
  - Extended `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
  - Updated `src/yuantus/meta_engine/tests/test_eco_main_chain_e2e.py`

## Verification
- `PYTHONPATH=src python3 -m pytest -q src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py src/yuantus/meta_engine/tests/test_eco_main_chain_e2e.py src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py`
- `PYTHONPATH=src python3 -m py_compile src/yuantus/meta_engine/services/release_validation.py src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py src/yuantus/meta_engine/tests/test_eco_main_chain_e2e.py`

## Observed Result
- `31 passed, 1 warning`
- `py_compile` passed
