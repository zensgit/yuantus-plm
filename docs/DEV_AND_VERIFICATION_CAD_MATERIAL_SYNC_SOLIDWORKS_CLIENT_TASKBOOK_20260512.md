# Development And Verification: SolidWorks Client Taskbook

## 1. Summary

This change adds a taskbook for the real SolidWorks CAD Material Sync client
implementation. It does not implement the client runtime. The goal is to make
the next Claude or Windows-capable worker slice executable and reviewable while
preserving the current truth: SolidWorks runtime acceptance is still pending.

## 2. Files

- `docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_SOLIDWORKS_CLIENT_R1_20260512.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_CLIENT_TASKBOOK_20260512.md`
- `src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The taskbook turns the remaining SolidWorks TODO items into a bounded R1
implementation sequence:

- R1.1 creates `clients/solidworks-material-sync/` and the field adapter.
- R1.2 wires local `/api/v1/plugins/cad-material-sync/diff/preview`
  confirmation and COM write-back.
- R1.3 fills real Windows SolidWorks evidence and runs
  `scripts/validate_cad_material_solidworks_windows_evidence.py`.

The taskbook explicitly keeps the TODO parent items unchecked until real
Windows evidence is accepted. This avoids confusing SDK-free fixtures with a
runtime SolidWorks acceptance signal.

## 4. Scope Control

Included:

- Claude taskbook for the next real SolidWorks client implementation.
- Contract test that pins required taskbook content, CI wiring, doc-index
  entries, and TODO state.
- CI contract list registration.
- Delivery doc index entries.

Excluded:

- No `clients/solidworks-material-sync/` runtime code.
- No SolidWorks SDK or COM build.
- No server API change.
- No filled Windows evidence.
- No TODO parent completion.

## 5. Contract Coverage

The new contract asserts:

- The taskbook names the real target path `clients/solidworks-material-sync/`.
- The field adapter scope mentions `CustomPropertyManager`, `Get6`, `GetAll3`,
  and cut-list/table-backed values.
- The confirmation path uses
  `/api/v1/plugins/cad-material-sync/diff/preview`, `cad_system=solidworks`,
  and `write_cad_fields`.
- The Windows acceptance path requires
  `scripts/validate_cad_material_solidworks_windows_evidence.py`.
- Binary artifacts, secrets, fake evidence, and premature TODO completion are
  explicitly forbidden.
- The two SolidWorks parent TODO items remain unchecked.
- CI and delivery doc index include the new taskbook contract and docs.

## 6. Verification Commands

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_fixture_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_diff_confirm_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_windows_evidence_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_material_sync_solidworks_client_taskbook_contracts.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py
```

```bash
git diff --check
```

## 7. Expected Result

All checks should pass without Windows or SolidWorks installed. The taskbook is
documentation and contract scaffolding only; the real implementation remains a
separate task that needs Windows evidence.

## 8. Review Notes

Reviewers should treat this as a planning and guardrail PR. It moves the plan
forward by removing ambiguity for the next implementation worker, but it should
not be interpreted as SolidWorks runtime support being complete.

