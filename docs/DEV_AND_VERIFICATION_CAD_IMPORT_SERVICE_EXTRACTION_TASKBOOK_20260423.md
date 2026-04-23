# DEV AND VERIFICATION: CadImportService Extraction Taskbook

Date: 2026-04-23

## 1. Goal

Record the P3 planning gate for extracting CAD import business logic from `cad_import_router.py` into a dedicated `CadImportService`.

This is a docs-only bounded increment. It does not change runtime code.

## 2. Delivered Files

- `docs/DEVELOPMENT_CLAUDE_TASK_CAD_IMPORT_SERVICE_EXTRACTION_20260423.md`
- `docs/DEV_AND_VERIFICATION_CAD_IMPORT_SERVICE_EXTRACTION_TASKBOOK_20260423.md`
- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Discovery Summary

Current `cad_import_router.py` inventory:

- 924 LOC.
- 1 public route: `POST /api/v1/cad/import`.
- Router currently owns file validation, checksum, duplicate repair, quota checks, CAD metadata resolution, auto Part creation, attachment linking, version/file lock guards, job planning, enqueue payloads, and response URL assembly.

Existing guard surface:

- `test_cad_import_router_contracts.py` proves route ownership and uniqueness.
- `test_cad_import_lock_guards.py` covers current-version file lock behavior.
- `test_ci_contracts_cad_import_dedup_index.py` protects dedup index payload support.

## 4. Taskbook Decisions

The taskbook locks the next implementation PR to a service extraction:

- New target module: `src/yuantus/meta_engine/services/cad_import_service.py`.
- Router remains the HTTP boundary.
- Service owns business logic and returns explicit result objects.
- Public `POST /api/v1/cad/import` route, form fields, defaults, response fields, status codes, and quota warning headers must remain unchanged.

The taskbook requires explicit request/result dataclasses:

- `CadImportRequest`
- `CadImportResult`
- `CadImportJobResult`

The exact names may change only if the implementation keeps the same separation and review clarity.

## 5. Hard Preservation Points

The implementation PR must preserve:

- Duplicate file behavior, including missing storage repair.
- `X-Quota-Warning` soft quota header.
- `dedup_index` in `cad_dedup_vision` payload.
- Authorization header propagation into job payloads.
- Tenant, org, user id, roles, CAD metadata, and optional `item_id` in every job payload.
- Auto Part creation and existing Part update semantics.
- Current-version file editability guards.
- `create_extract_job=None` defaulting to CAD-file dependent behavior.
- `create_geometry_job=None` defaulting to disabled behavior.

## 6. Explicit Non-Goals

- No schema or migration changes.
- No new CAD import API version.
- No file storage layout change.
- No worker task type or priority change.
- No scheduler trigger.
- No shared-dev 142 interaction.
- No FreeCAD, STEP/IGES backend, CAD profile, or UI work.

## 7. Verification

Docs-only verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `3 passed`.

Whitespace:

```bash
git diff --check
```

Result: passed.

## 8. Next Step

After Codex review, the implementation PR should use:

```text
docs/DEVELOPMENT_CLAUDE_TASK_CAD_IMPORT_SERVICE_EXTRACTION_20260423.md
```

as the source of truth.

Implementation should be done as a separate bounded PR, not bundled with this taskbook PR.
