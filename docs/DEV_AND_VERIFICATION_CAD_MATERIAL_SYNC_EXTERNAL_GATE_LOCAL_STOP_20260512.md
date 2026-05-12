# Development And Verification: CAD Material Sync External Gate Local Stop

Date: 2026-05-12

Path:
`docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_EXTERNAL_GATE_LOCAL_STOP_20260512.md`

## 1. Summary

This document records the local stop point for the CAD Material Sync line after
the AutoCAD delivery package, AutoCAD external validation handoff, SolidWorks
SDK-free client sequence, SolidWorks Windows runbook, and SolidWorks external
handoff have all landed on `main`.

The repository-side contracts, fixtures, runbooks, handoff packets, and evidence
validators are now in place. The remaining work is not another macOS/local
implementation slice. The remaining work requires real Windows CAD operator
execution:

- Windows + AutoCAD 2018 DLL build/load and real DWG write-back smoke.
- Windows + AutoCAD 2024 regression smoke.
- Windows + SolidWorks Add-in/COM field read, diff preview, confirm/cancel,
  write-back, save/reopen, and evidence validation.

## 2. Decision

Do not mark the CAD Material Sync TODO parents complete from local tests, mock
fixtures, SDK-free contracts, documentation, or generated evidence.

Do not start another local-only CAD Material Sync "continue" PR unless it is
one of the allowed PR shapes in section 5.

## 3. Canonical Inputs

Use these artifacts for the next real external validation step:

- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_EXTERNAL_VALIDATION_HANDOFF_20260511.md`
- `docs/CAD_MATERIAL_SYNC_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`
- `scripts/validate_cad_material_windows_evidence.py`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_EXTERNAL_HANDOFF_20260512.md`
- `docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md`
- `scripts/validate_cad_material_solidworks_windows_evidence.py`

## 4. Current Open TODOs

These TODOs remain intentionally open:

- `CAD 客户端适配层`
- `SolidWorks 明细表/属性表字段读取。`
- `真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。`
- `SolidWorks 本地客户端可视化差异预览和确认写回 UI。`
- `真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。`
- `更完整验证`
- `在 Windows + AutoCAD 2018 环境编译 DLL 并做真实 DWG 手工 smoke。`
- `在 Windows + AutoCAD 2024 环境做回归 smoke，确保高版本路径未退化。`

The parent items stay unchecked because accepted real Windows CAD evidence does
not exist yet.

## 5. Allowed Next PR Shapes

Only these follow-up PR shapes are in scope without redefining the plan:

1. AutoCAD evidence signoff PR:
   - records accepted real Windows + AutoCAD 2018 evidence.
   - optionally records AutoCAD 2024 regression evidence.
   - includes output from
     `scripts/validate_cad_material_windows_evidence.py`.
   - does not add binaries, secrets, production DWG files, or runtime behavior.
2. SolidWorks evidence signoff PR:
   - records accepted real Windows + SolidWorks evidence.
   - includes output from
     `scripts/validate_cad_material_solidworks_windows_evidence.py`.
   - does not add binaries, secrets, production CAD files, or mock evidence.
3. Real SolidWorks implementation PR:
   - is produced from a Windows + SolidWorks-capable environment.
   - includes real build/load/read/write/save-reopen evidence.
   - keeps SDK-free fixture output separate from real evidence.
4. Independent triggered taskbook:
   - explicitly outside this CAD Material Sync external validation line.
   - names the new trigger, scope, non-goals, and verification plan.

## 6. Stop Gates

Stop rather than continue when any of these is true:

- no Windows workstation is available.
- no AutoCAD 2018 installation is available for the minimum-baseline smoke.
- no AutoCAD 2024 installation is available for the regression smoke.
- no SolidWorks installation is available.
- the evidence file is generated from mock, fixture, or SDK-free output.
- evidence validator output is missing or failing.
- evidence contains plaintext secrets, bearer tokens, tenant tokens, customer
  names, production CAD paths, or unredacted customer drawing content.
- a PR proposes to check TODO parent items without accepted real external
  evidence.

## 7. Non-Goals

- No runtime code changes.
- No AutoCAD or SolidWorks binary artifact.
- No COM registration.
- No mock evidence acceptance.
- No production CAD file modification.
- No TODO parent completion.
- No Phase 5 implementation.
- No P3.4 evidence creation or acceptance.

## 8. Verification Commands

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_gate_local_stop_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_gate_local_stop_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_validation_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_external_handoff_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

```bash
python3 -m py_compile \
  src/yuantus/meta_engine/tests/test_cad_material_sync_external_gate_local_stop_contracts.py
```

```bash
git diff --check
```

## 9. Verification Results

- CAD Material Sync external gate local-stop contract -> `5 passed`.
- Focused gate/handoff/doc-index/CI suite -> `24 passed`.
- Python compile:
  `python3 -m py_compile src/yuantus/meta_engine/tests/test_cad_material_sync_external_gate_local_stop_contracts.py`
  -> passed.
- `git diff --check` -> clean.

## 10. Reviewer Checklist

- Confirm this is a stop-gate record, not a CAD runtime implementation.
- Confirm the AutoCAD and SolidWorks evidence validators remain the acceptance
  boundary.
- Confirm mock, fixture, SDK-free, and documentation-only outputs cannot mark
  TODO parents complete.
- Confirm the only remaining unblocked path is real external Windows CAD
  evidence or an explicitly separate triggered taskbook.
