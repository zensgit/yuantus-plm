# DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420

## Goal

Add an operator-safe verifier for tenant/org scoped CAD backend profile overrides so the new management surface can be checked on local, shared-dev, or customer-like environments without leaving scope overrides behind.

## Scope

This round adds only the operational verifier and its discoverability/contracts. It does not change backend profile semantics.

## What Changed

### 1. Added a scoped verification script

- File:
  - `scripts/verify_cad_backend_profile_scope.sh`

Behavior:

1. Reads auth from either `TOKEN` or `LOGIN_USERNAME` + `PASSWORD`.
2. Supports `--env-file "$HOME/.config/yuantus/p2-shared-dev.env"` style loading.
3. Verifies:
   - `GET /api/v1/cad/backend-profile`
   - `PUT /api/v1/cad/backend-profile`
   - `DELETE /api/v1/cad/backend-profile?scope=org|tenant`
   - `GET /api/v1/cad/capabilities`
4. Restores the original org-scope state before exit.
5. Skips tenant-default verification when an active org override masks the tenant-default read surface.

Why `LOGIN_USERNAME` instead of plain `USERNAME`:

- shell sessions often already export `USERNAME=<current-os-user>`
- using a dedicated variable avoids accidental login attempts as the workstation user and keeps the documented default `admin` behavior real

Operational constraint:

- do not run the verifier concurrently against the same tenant/org scope
- it temporarily writes scoped config and then restores it, so parallel runs against one scope can observe each other's intermediate state

### 2. Added discoverability docs

- Files:
  - `docs/CAD_CONNECTORS.md`
  - `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

Docs now point operators to the verifier and describe the restore/masked-scope behavior.

### 3. Added contract coverage

- Files:
  - `src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py`
  - `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

Coverage:

- shell syntax stays valid
- `--help` stays usable
- scripts index entry stays present
- `CAD_CONNECTORS.md` keeps the verifier discoverable
- this dev-and-verification record stays indexed

## Verification

Shell checks:

```bash
bash -n scripts/verify_cad_backend_profile_scope.sh
bash scripts/verify_cad_backend_profile_scope.sh --help
```

Focused tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_service.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## Result

- verifier script is runnable and repo-safe
- docs and script index advertise the verifier
- the new dev doc is indexed and sorting-safe

## Files Changed

- `scripts/verify_cad_backend_profile_scope.sh`
- `docs/CAD_CONNECTORS.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_cad_backend_profile_scope_verifier.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

## Claude Code CLI Note

Claude Code CLI was used in non-interactive `-p` mode as a sidecar reviewer for the closeout checklist only. The implementation and final edits remained on the main line in this worktree.
