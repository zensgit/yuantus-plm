# DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_LOCAL_SMOKE_20260420

## Goal

Run the new CAD backend profile scope verifier against a real local API instance and confirm both authentication paths and both scope flows behave as designed.

## Environment

- local only
- `local-dev-env` sqlite seed
- base URL: `http://127.0.0.1:7910`
- tenant/org: `tenant-1` / `org-1`

Boundary:

- this is not shared-dev
- this validates the verifier workflow and backend-profile management surface without touching a shared environment

## What Was Validated

### 1. Local API instance

- `local-dev-env/start.sh` reset the DB, ran migrations, seeded identity/meta/ECO fixtures.
- For this terminal executor, the detached `nohup uvicorn` path did not stay attached reliably.
- The smoke used a PTY-held `uvicorn` process instead, without changing repo code.

### 2. `LOGIN_USERNAME` path

Command:

```bash
BASE_URL=http://127.0.0.1:7910 \
LOGIN_USERNAME=admin PASSWORD=admin \
TENANT_ID=tenant-1 ORG_ID=org-1 \
OUTPUT_DIR=./tmp/cad-backend-profile-scope-local-login-r2-20260420 \
bash scripts/verify_cad_backend_profile_scope.sh
```

Result:

- `ALL CHECKS PASSED`
- org scope write/read/restore passed
- tenant-default write/read/restore passed
- final state restored to `effective=local-baseline`, `source=legacy-mode`

### 3. `TOKEN` path

Command:

```bash
TOKEN=$(curl -sS -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

BASE_URL=http://127.0.0.1:7910 \
TOKEN=$TOKEN TENANT_ID=tenant-1 ORG_ID=org-1 \
OUTPUT_DIR=./tmp/cad-backend-profile-scope-local-token-r2-20260420 \
bash scripts/verify_cad_backend_profile_scope.sh
```

Result:

- `ALL CHECKS PASSED`
- same org/tenant scope checks passed
- final state restored to `effective=local-baseline`, `source=legacy-mode`

## Real Findings

### 1. Fixed a login-variable bug in the verifier

Observed issue:

- plain `USERNAME` was polluted by the workstation shell environment (`USERNAME=chouhua`)
- documented default `admin` behavior was therefore not real

Fix:

- switched the script contract to `LOGIN_USERNAME`
- updated docs and contract tests accordingly

### 2. Added a concurrency warning

Observed issue:

- running two verifier instances in parallel against the same tenant/org scope makes them observe each other's temporary override state

Fix:

- added an explicit "do not run concurrently against the same tenant/org scope" note to help/docs

## Verification

Shell:

```bash
bash -n scripts/verify_cad_backend_profile_scope.sh
bash scripts/verify_cad_backend_profile_scope.sh --help
```

Focused tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Result:

- shell/help checks passed
- focused contracts/docs checks passed
- local smoke passed for both auth paths

## Artifacts

- `tmp/cad-backend-profile-scope-local-login-r2-20260420/README.txt`
- `tmp/cad-backend-profile-scope-local-token-r2-20260420/README.txt`

## Files Updated In This Round

- `scripts/verify_cad_backend_profile_scope.sh`
- `docs/CAD_CONNECTORS.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md`
- `docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_LOCAL_SMOKE_20260420.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py`

## Claude Code CLI Note

Claude Code CLI was used in non-interactive `-p` mode as a sidecar reviewer for what to lock down around the verifier. It did not edit files in this worktree.
