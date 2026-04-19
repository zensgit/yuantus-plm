# DEV AND VERIFICATION — SHARED DEV FIRST-RUN POLISH — 2026-04-19

## Development

- Normalized the generated shared-dev `BASE_URL` placeholder to `https://change-me-shared-dev-host` so the helper, printed first-run commands, bootstrap handoff, and bootstrap completion message all use the same placeholder style.
- Tightened `scripts/validate_p2_shared_dev_env.sh` so it rejects placeholder values containing `change-me` anywhere in the string, including URL-shaped placeholders.
- Restored missing artifact expectations in the first-run/bootstrap/rerun handoff material:
  - `summary_probe.json` for precheck evidence
  - `README.txt` for canonical wrapper output evidence

## Verification

- `python3 -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py`
- `bash -n scripts/bootstrap_shared_dev.sh`
- `bash -n scripts/generate_p2_shared_dev_bootstrap_env.sh`
- `bash -n scripts/validate_p2_shared_dev_env.sh`
- `bash -n scripts/print_p2_shared_dev_bootstrap_commands.sh`
- `bash -n scripts/print_p2_shared_dev_first_run_commands.sh`
- `bash -n scripts/print_p2_shared_dev_observation_commands.sh`
- `bash scripts/print_p2_shared_dev_first_run_commands.sh | sed -n '1,120p'`
- `bash scripts/print_p2_shared_dev_observation_commands.sh | sed -n '1,120p'`

## Result

- The shared-dev first-run and rerun handoff path is now internally consistent at the local helper layer.
- Operators no longer get a generated `BASE_URL` placeholder that immediately fails the validator for a different placeholder convention.
- The documented evidence set now matches the actual precheck and canonical wrapper outputs.
