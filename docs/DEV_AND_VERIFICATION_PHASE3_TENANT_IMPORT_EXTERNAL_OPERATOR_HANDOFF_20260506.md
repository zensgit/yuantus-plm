# Dev & Verification - Phase 3 Tenant Import External Operator Handoff

Date: 2026-05-06

## 1. Summary

This document records the post-`b9f41c0` P3.4 tenant-import boundary.

The repository-side P3.4 toolchain is complete through DB-free operator safety
gates, shell/Python CLI redaction, command validation, full-closeout wrapper
support, synthetic drill, and reviewer-packet generation. The remaining P3.4
work is external operator execution against real non-production PostgreSQL
source/target databases.

## 2. Current Mainline

- Mainline anchor: `b9f41c0` (`test: make tenant import shell tests use active python (#483)`).
- Local toolchain status: clean on `origin/main`.
- Runtime cutover status: blocked.
- `TENANCY_MODE=schema-per-tenant` production enablement: not authorized.
- Real rehearsal evidence: not present.

## 3. Design Decision

No additional local development should try to close P3.4 without real operator
evidence.

The unchecked TODO items across the tenant-import documents are all one of:

- external operator inputs, such as real non-production DSNs, an approved
  rehearsal window, a backup/restore owner, and signed classification evidence;
- external execution, such as row-copy rehearsal and reviewer-packet generation
  from real outputs;
- explicit non-goals, such as production cutover, runtime tenant-mode
  enablement, or automatic rollback.

Adding another local bypass, mock evidence path, or simulated row-copy output
would weaken the stop gate. The correct next action is to hand the existing
toolchain to an operator and preserve `ready_for_cutover=false` until real
evidence exists.

## 4. Operator Handoff Path

Use `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` as the canonical runbook.

The shortest approved external path is:

```bash
scripts/generate_tenant_import_rehearsal_env_template.sh \
  --out "$HOME/.config/yuantus/tenant-import-rehearsal.env"
```

Then the operator edits the repo-external file with real non-production DSNs and
prechecks it without opening a database connection:

```bash
scripts/precheck_tenant_import_rehearsal_env_file.sh \
  --env-file "$HOME/.config/yuantus/tenant-import-rehearsal.env"
```

During the approved rehearsal window, run:

```bash
scripts/run_tenant_import_rehearsal_full_closeout.sh \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --artifact-prefix output/tenant_<tenant-id> \
  --backup-restore-owner "<owner>" \
  --rehearsal-window "<window>" \
  --rehearsal-executed-by "<operator>" \
  --evidence-reviewer "<reviewer>" \
  --date "<yyyy-mm-dd>" \
  --env-file "$HOME/.config/yuantus/tenant-import-rehearsal.env" \
  --confirm-rehearsal \
  --confirm-closeout
```

The generated reviewer packet is the first artifact that can move P3.4 from
local-ready to evidence-review. It still must keep `Ready for cutover: false`.

## 5. Synthetic Drill Boundary

The synthetic drill remains useful for local command-path rehearsal:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_synthetic_drill \
  --artifact-dir output/tenant_<tenant-id>_synthetic_drill \
  --artifact-prefix tenant_<tenant-id>_synthetic_drill \
  --output-json output/tenant_<tenant-id>_synthetic_drill.json \
  --output-md output/tenant_<tenant-id>_synthetic_drill.md \
  --strict
```

It must not be attached as real evidence. The expected safety fields are:

- `Synthetic drill: true`
- `Real rehearsal evidence: false`
- `DB connection attempted: false`
- `Ready for cutover: false`

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_synthetic_drill.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal*.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m yuantus.scripts.tenant_import_rehearsal_synthetic_drill \
  --artifact-dir output/tenant_codex_external_handoff_synthetic_drill \
  --artifact-prefix tenant_codex_external_handoff_synthetic_drill \
  --output-json output/tenant_codex_external_handoff_synthetic_drill.json \
  --output-md output/tenant_codex_external_handoff_synthetic_drill.md \
  --strict

git diff --check
```

## 7. Verification Results

- Focused stop-gate, synthetic drill, and doc-index suite: 21 passed in 0.15s.
- Full tenant-import family plus doc-index regression: 329 passed, 1 skipped,
  1 warning in 12.95s.
- Synthetic drill smoke: passed with `Synthetic drill: true`,
  `Real rehearsal evidence: false`, `DB connection attempted: false`, and
  `Ready for cutover: false`.
- `git diff --check`: clean.

## 8. Non-Goals

- Do not connect to any source or target database in this PR.
- Do not execute row-copy.
- Do not create, accept, or synthesize operator evidence.
- Do not mark P3.4 rehearsal complete.
- Do not enable production cutover.
- Do not enable runtime `TENANCY_MODE=schema-per-tenant`.

## 9. Reviewer Checklist

- Confirm the document keeps P3.4 blocked on real operator evidence.
- Confirm the handoff commands point to the existing runbook path.
- Confirm synthetic drill output is explicitly excluded from real evidence.
- Confirm all verification remains DB-free.
- Confirm the delivery-doc index entry is alphabetically sorted.
