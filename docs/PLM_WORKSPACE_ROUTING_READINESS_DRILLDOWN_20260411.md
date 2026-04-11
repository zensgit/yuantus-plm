# PLM Workspace Routing Readiness Drilldown

## Goal

Promote routing readiness resources from boundary-only inspection to a native
workspace detail drilldown that can:

- open routing detail from release readiness
- expose released operations in the native detail surface
- preserve source-part recovery back to the governed Part
- keep baseline readiness resources boundary-limited

No backend routes were added. The implementation uses the existing routing APIs.

## Design

### 1. Partial native support for routing readiness

Routing readiness resources now support:

- `Open Detail`

Routing readiness resources still do not support:

- `Use In Explorer`
- `Open BOM`

Reason:
the available backend contract already exposes stable routing identity and
operation detail, but not a routing-native BOM or explorer surface.

### 2. Existing APIs used

The routing drilldown is built only from:

- `GET /api/v1/routings/{routing_id}`
- `GET /api/v1/routings/{routing_id}/operations`

The workspace synthesizes a routing-native detail payload with:

- routing identity/state
- routing code/version/plant/line
- source `item_id`
- source `mbom_id`
- released operations list

### 3. Boundary semantics stay explicit

When the active workspace object is `Routing`, these surfaces now return explicit
boundary copy instead of failed AML/API calls:

- metadata
- BOM
- where-used
- files
- AML related documents
- approval rail
- release readiness

Rule:
native routing workspace is a detail-only manufacturing sub-context. Change,
documents, structure, governance, and readiness stay owned by the source Part.

### 4. Source recovery is first-class

Routing detail renders source recovery actions:

- `Return to Source Part`
- `Return to Source Change`

This keeps release-readiness drilldown reversible and preserves the product
context as the system of record.

### 5. Baseline remains boundary-limited

This slice does not add baseline native drilldown. Baseline readiness resources
remain inspectable but disabled for explorer/detail/BOM handoff.

## Files Changed

- `src/yuantus/web/plm_workspace.html`
- `playwright/tests/plm_workspace_demo_resume.spec.js`
- `playwright/tests/README_plm_workspace.md`

## Verification

### Pytest

Command:

```bash
./.venv/bin/python -m pytest \
  src/yuantus/api/tests/test_plm_workspace_router.py \
  src/yuantus/api/tests/test_workbench_router.py \
  -q
```

Result:

```text
7 passed
```

### Target Playwright

Command:

```bash
npx playwright test playwright/tests/plm_workspace_demo_resume.spec.js --reporter=line
```

Result:

```text
5 passed
```

### Full Native Workspace Bundle

Command:

```bash
npx playwright test \
  playwright/tests/plm_workspace_documents_ui.spec.js \
  playwright/tests/plm_workspace_demo_resume.spec.js \
  playwright/tests/plm_workspace_document_handoff.spec.js \
  --reporter=line
```

Result:

```text
13 passed
```

## Verified User Flow

`Config Parent -> Change -> Load Release Readiness -> Routing resource -> Open Detail`

Verified outcome:

- active object switches to `Routing:<id>`
- routing detail renders routing facts and released operations
- source recovery returns to the source `Part`

`Config Parent -> Change -> Load Release Readiness -> Baseline resource`

Verified outcome:

- baseline remains boundary-limited
- explorer/detail/BOM handoff buttons stay disabled

## Non-Goals

- no backend API changes
- no routing BOM surface
- no baseline native drilldown
- no Metasheet/Wave 2 contract work
