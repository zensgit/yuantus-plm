# DEVELOPMENT Task - CadImportService Extraction - 2026-04-23

## 1. Goal

Reduce `src/yuantus/meta_engine/web/cad_import_router.py` complexity by extracting CAD import business logic into a service while preserving the public `POST /api/v1/cad/import` contract.

This is a bounded architecture increment after CAD router decomposition R12. The route already lives in `cad_import_router.py`; this task is not another router split. It is a router-to-service extraction.

## 2. Current Inventory

Measured on `main` after PR #377.

`src/yuantus/meta_engine/web/cad_import_router.py`:

- 924 LOC.
- 1 public route: `POST /cad/import`.
- Route body owns upload validation, checksum / duplicate lookup, storage repair, quota checks, CAD metadata resolution, auto Part creation, item-file linking, version/file lock guards, job planning, job enqueueing, and response URL assembly.

Existing focused tests and contracts:

- `src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py`
- CAD router ownership contract family under `test_cad_*_router_contracts.py`

## 3. Target Shape

Add a new service module:

```text
src/yuantus/meta_engine/services/cad_import_service.py
```

The router should remain responsible for:

- FastAPI declarations: `APIRouter`, `File`, `Form`, `Depends`, `Request`, `Response`.
- Reading `UploadFile` bytes.
- Passing request headers and form values into the service.
- Setting quota warning response headers returned by the service.
- Constructing the existing `CadImportResponse` pydantic response, including request-dependent viewer URL rewriting.
- Mapping service exceptions to the same HTTP status / detail payloads currently returned.

The service should own:

- Upload validation against settings.
- Checksum calculation and duplicate file lookup.
- Missing storage repair for duplicate files.
- New file quota evaluation and storage write.
- CAD metadata / connector resolution.
- Auto Part creation or existing Part update.
- Item attachment / link update.
- Current-version file editability guard checks.
- Job planning quota evaluation.
- Job enqueue payload construction and `JobService.create_job()` calls.

## 4. Service Interface

Use explicit data objects rather than passing raw FastAPI objects into the service.

Required input object:

```python
@dataclass
class CadImportRequest:
    filename: str
    content: bytes
    item_id: Optional[str]
    file_role: str
    author: Optional[str]
    source_system: Optional[str]
    source_version: Optional[str]
    document_version: Optional[str]
    cad_format: Optional[str]
    cad_connector_id: Optional[str]
    create_preview_job: bool
    create_geometry_job: Optional[bool]
    geometry_format: str
    create_extract_job: Optional[bool]
    create_bom_job: bool
    auto_create_part: bool
    create_dedup_job: bool
    dedup_mode: str
    dedup_index: bool
    create_ml_job: bool
    authorization: Optional[str]
```

Required result object:

```python
@dataclass
class CadImportResult:
    file_container: FileContainer
    is_duplicate: bool
    item_id: Optional[str]
    attachment_id: Optional[str]
    jobs: list[CadImportJobResult]
    quota_warnings: list[str]
```

Required job result object:

```python
@dataclass
class CadImportJobResult:
    id: str
    task_type: str
    status: str
```

Service method:

```python
class CadImportService:
    def __init__(self, db: Session, identity_db: Session):
        ...

    def import_file(self, request: CadImportRequest, user: CurrentUser) -> CadImportResult:
        ...
```

The exact dataclass names may be adjusted only if the implementation keeps the same separation and review clarity.

## 5. Exception Contract

Do not let the service raise arbitrary `HTTPException` from newly extracted business logic. Add small service exceptions and map them in the router.

Minimum exception shape:

```python
class CadImportError(Exception):
    status_code: int
    detail: Any
```

Allowed subclasses:

- `CadImportValidationError`
- `CadImportConflictError`
- `CadImportQuotaError`
- `CadImportUpstreamError`

Router mapping must preserve existing status codes and details:

| Scenario | Current status | Must remain |
| --- | ---: | --- |
| Empty file | 400 | 400 |
| File too large | 413 | 413 |
| Disallowed extension | 415 | 415 |
| Hard quota exceeded | 429 | 429 |
| Part ItemType missing | 404 | 404 |
| CAD attribute extraction fatal error | 502 | 502 |
| Generic CAD attribute extraction error | 400 | 400 |
| PLMException from AML apply | original `exc.status_code` | unchanged |
| Item not found | 404 | 404 |
| Version/file lock conflict | 409 | 409 |
| Version/file guard validation error | 400 | 400 |
| JobService quota error | original `exc.status_code` | unchanged |

## 6. Co-Move Rules

Move these helpers into `cad_import_service.py` unless implementation proves they must remain router-local:

- `_ensure_current_version_attachment_editable`
- `_ensure_duplicate_file_repair_editable`
- `_calculate_checksum`
- `_get_mime_type`
- `_validate_upload`
- `_json_text`
- `_normalize_text`
- `_parse_filename_attrs`
- `_build_auto_part_properties`
- `_build_missing_updates`
- `_get_cad_format`
- `_resolve_cad_metadata`

Keep router-local:

- `CadImportJob` and `CadImportResponse` pydantic API response models.
- `_build_cad_viewer_url()` because it depends on `Request.url_for()` and public CADGF router URL settings.
- FastAPI form parameter declarations.

If a helper remains in the router, the implementation PR must justify it in the delivery MD.

## 7. Required Behavior Preservation

The implementation must preserve:

- Public route path, method, request form fields, defaults, and response model.
- `X-Quota-Warning` header behavior for soft quota decisions.
- Duplicate file behavior, including missing storage object repair.
- `dedup_index` in `cad_dedup_vision` payload.
- Authorization header propagation into job payloads.
- Tenant, org, user id, and roles propagation into every job payload.
- `create_bom_job` guard requiring `item_id` or `auto_create_part`.
- Auto Part creation and existing Part update semantics.
- Current-version file editability guards for existing and new links.
- `create_extract_job=None` defaulting to CAD-file dependent behavior.
- `create_geometry_job=None` defaulting to disabled behavior.
- Response URL fields and CAD metadata fields.

## 8. Implementation Constraints

- Do not change schema, migrations, settings, or environment variables.
- Do not change public API paths or response field names.
- Do not change CAD connector registry behavior.
- Do not change quota policy.
- Do not change `JobService.create_job()` behavior or dedupe semantics.
- Do not change worker task types or priorities.
- Do not touch shared-dev 142.
- Do not combine this with CAD backend profile, FreeCAD fallback, scheduler, or UI work.
- Do not delete `cad_import_router.py`; it remains the HTTP boundary.

## 9. Required Tests

Add:

```text
src/yuantus/meta_engine/tests/test_cad_import_service.py
```

At minimum cover:

1. New file hard quota exceeded maps to `CadImportQuotaError` with 429 payload.
2. Duplicate file with missing storage calls duplicate repair guard before re-upload.
3. `create_bom_job=True` without `item_id` and without auto-created Part raises 400.
4. Auto Part creation updates an existing Part with missing CAD-synced fields.
5. Auto Part creation creates a new Part and returns its `item_id`.
6. Existing item-file link role update checks current-version editability for old and new roles.
7. New item-file link checks current-version editability before insert.
8. Job planning counts only enabled jobs and enforces active job quota before enqueue.
9. Enqueued payload includes `file_id`, `source_path`, `tenant_id`, `org_id`, `user_id`, `roles`, `authorization`, CAD metadata, and optional `item_id`.
10. Dedup job payload preserves `mode`, `user_name`, and `index`.

Update existing tests as needed:

- `test_cad_import_lock_guards.py` may patch `CadImportService` if the lock guard moves behind the service boundary, but it must still prove HTTP 409/400 mapping.
- `test_cad_import_router_contracts.py` must still prove `POST /api/v1/cad/import` is registered exactly once.

Add a static contract test if useful:

- `cad_import_router.py` should not directly import `JobService`, `QuotaService`, `AMLEngine`, `CadService`, or `VersionFileService` after extraction.

## 10. Verification Commands

Compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_import_router.py \
  src/yuantus/meta_engine/services/cad_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_import_service.py
```

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py \
  src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_import_dedup_index.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_mesh_stats_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_properties_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_review_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_sync_template_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_view_state_router_contracts.py
```

Doc contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Whitespace:

```bash
git diff --check
```

Pact provider is optional for this implementation because public route surface is unchanged. If the implementation changes response model or status mapping, pact provider becomes mandatory.

## 11. Review Checklist

| # | Check |
| --- | --- |
| 1 | `POST /api/v1/cad/import` remains registered exactly once. |
| 2 | Router no longer owns storage, quota, AML, lock guard, and job enqueue business logic. |
| 3 | Service uses explicit request/result dataclasses, not FastAPI `Request`, `Response`, or `UploadFile`. |
| 4 | Existing HTTP status codes and details are preserved. |
| 5 | Soft quota warnings still surface through `X-Quota-Warning`. |
| 6 | Duplicate storage repair and current-version editability guards are still covered by tests. |
| 7 | Auto Part creation behavior is unchanged for existing and new Parts. |
| 8 | Job payloads still include tenant/org/user/roles/auth and CAD metadata. |
| 9 | No schema, settings, scheduler, shared-dev 142, or UI changes. |
| 10 | Delivery MD documents any helper deliberately left in the router. |

## 12. Explicit Non-Goals

- Do not split more CAD routes; router decomposition is already complete.
- Do not introduce a new CAD import API version.
- Do not change file storage layout.
- Do not change CAD preview / geometry / extract / BOM / dedup / ML worker behavior.
- Do not add a scheduler trigger.
- Do not add frontend upload UI.
- Do not add FreeCAD, STEP/IGES backend, or CAD profile changes.
- Do not run shared-dev 142 first-run bootstrap.

## 13. Suggested Claude Code CLI Prompt

Use this exact taskbook as the implementation source of truth:

```text
Implement docs/DEVELOPMENT_CLAUDE_TASK_CAD_IMPORT_SERVICE_EXTRACTION_20260423.md.

Keep scope bounded:
- extract CAD import business logic into src/yuantus/meta_engine/services/cad_import_service.py
- keep POST /api/v1/cad/import public behavior unchanged
- add focused service tests and preserve existing router/lock guard contracts
- do not touch schema, scheduler, shared-dev 142, CAD profile, FreeCAD, or UI
- produce docs/DEV_AND_VERIFICATION_CAD_IMPORT_SERVICE_EXTRACTION_20260423.md and update docs/DELIVERY_DOC_INDEX.md

Run the verification commands and report exact results.
```

## 14. Execution Order

1. Implement the service and dataclasses.
2. Thin the router to HTTP parsing / exception mapping / response assembly.
3. Add service tests.
4. Update router tests only where patch paths or exception mapping moved.
5. Run focused verification.
6. Produce implementation `DEV_AND_VERIFICATION_*` MD.
7. Open a bounded PR for review.
