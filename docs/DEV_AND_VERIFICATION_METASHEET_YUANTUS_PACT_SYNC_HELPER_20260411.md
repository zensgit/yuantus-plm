# Metasheet <-> Yuantus Pact Sync Helper

Date: `2026-04-11`

## Goal

Remove the last manual step from the pact workflow on the Yuantus side:

- `metasheet2` remains the consumer pact source-of-truth
- `Yuantus` keeps a committed provider-side copy for local verification and CI
- syncing that copy should be one command, not tribal knowledge

## Design

Added script:

- `scripts/sync_metasheet2_pact.sh`

Responsibilities:

1. read the pact source from:
   `metasheet2/packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json`
2. compare it with the Yuantus copy at:
   `contracts/pacts/metasheet2-yuantus-plm.json`
3. either:
   - fail on drift with `--check`
   - or update the local copy with a normal sync run
4. optionally execute:
   `src/yuantus/api/tests/test_pact_provider_yuantus_plm.py`

The script deliberately does **not** author or mutate the consumer pact. It
only mirrors the committed consumer artifact into the provider repo.

## Interface

```bash
bash scripts/sync_metasheet2_pact.sh --check
bash scripts/sync_metasheet2_pact.sh
METASHEET2_ROOT=/path/to/metasheet2 \
  bash scripts/sync_metasheet2_pact.sh --verify-provider
```

Supported environment variables:

- `METASHEET2_ROOT`
- `PYTEST_BIN`
- `PROVIDER_TEST`

## Why This Matters

Without a helper, the workflow had a hidden manual dependency:

- update pact in `metasheet2`
- remember to copy the same JSON into `Yuantus`
- then remember the exact provider test invocation

That is error-prone for a shared-contract setup. The helper turns the workflow
into an explicit, repeatable command and gives reviewers one place to look.

## Verification

Commands executed in a clean Yuantus worktree:

```bash
bash scripts/sync_metasheet2_pact.sh --help

METASHEET2_ROOT=/tmp/metasheet2-pact-wave-sync-1k4fiv \
  bash scripts/sync_metasheet2_pact.sh --check

METASHEET2_ROOT=/tmp/metasheet2-pact-wave-sync-1k4fiv \
PYTEST_BIN=/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/pytest \
  bash scripts/sync_metasheet2_pact.sh --verify-provider

/Users/huazhou/Downloads/Github/Yuantus/.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_sync_helper.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py
```

Observed results:

- helper `--help` rendered expected usage and path contract
- `--check` returned:
  `pact_sync=ok source_hash=03df311fa986b809233553dccc0907457e1aa02cc733ca398d6114ae9401342b target_hash=03df311fa986b809233553dccc0907457e1aa02cc733ca398d6114ae9401342b`
- `--verify-provider` returned `1 passed, 3 warnings in 19.84s`
- combined contract, shell syntax, doc index, and provider verifier batch:
  `17 passed, 3 warnings in 19.84s`

## Files

- `scripts/sync_metasheet2_pact.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_pact_sync_helper.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`
