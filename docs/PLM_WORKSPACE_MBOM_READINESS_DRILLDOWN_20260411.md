# PLM Workspace MBOM Readiness Drilldown

## Goal

Promote MBOM readiness resources from inspect-only release-readiness entries to a
native workspace drilldown that can:

- open MBOM detail from release readiness
- open MBOM structure/BOM from release readiness
- preserve source-part recovery so the operator can return to the governed Part
- keep routing and baseline readiness resources boundary-limited

No backend route changes were required. The existing `GET /api/v1/mboms/{mbom_id}`
endpoint is the sole MBOM drilldown data source.

## Design

### 1. Treat MBOM as a first-class workspace object type

`release_readiness -> handoff` no longer maps `mbom` to `Part`.

- `mapResourceTypeToWorkspaceItemType("mbom") -> "MBOM"`
- `readinessResourceHandoffSupport("mbom")` enables `detail` and `bom`
- `select/explorer` remains disabled for MBOM

Reason:
MBOM drilldown is not AML explorer context. Reusing `Part` caused the workspace to
hit AML metadata, where-used, file, and related-document paths that do not apply.

### 2. Add MBOM-native detail and structure fetch paths

`plm_workspace.html` now special-cases `itemType === "MBOM"` for:

- `loadDetail()`
- `loadBom()`
- `syncWorkspaceForCurrentObject()`

The workspace builds a synthetic MBOM detail payload from:

- `GET /api/v1/mboms/{mbom_id}?include_operations=true`
- the selected release-readiness resource name/state

That gives the UI a stable identity surface:

- `type = MBOM`
- `name = readiness resource name`
- `structure = mbom tree payload`
- `source_item_*` facts for the originating Part

### 3. Keep unsupported surfaces explicit, not broken

For MBOM active-object context, the workspace now returns boundary copy instead of
erroring for:

- metadata
- where-used
- files
- AML related documents
- approval rail
- release readiness

Rule:
MBOM native workspace supports detail and structure only. Governance, document
surfaces, and readiness remain owned by the source Part.

### 4. Add source recovery on both MBOM detail and BOM surfaces

MBOM drilldown stores the current Part as `handoffSource` before switching
context. Both detail and BOM views render source recovery actions:

- `Return to Source Part`
- `Return to Source Change`

This keeps the readiness flow reversible and avoids trapping the operator in a
manufacturing-only sub-context.

### 5. Preserve routing/baseline boundaries

Routing and baseline readiness resources still do not expose native explorer,
detail, or BOM handoff. Existing boundary-limited behavior was preserved.

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
4 passed
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
12 passed
```

## Verified User Flow

`Config Parent -> Change -> Load Release Readiness -> MBOM resource -> Open Detail`

- active object switches to `MBOM:<id>`
- MBOM detail renders source-part context and source recovery

`Config Parent -> Change -> Load Release Readiness -> MBOM resource -> Open BOM`

- active object switches to `MBOM:<id>`
- MBOM structure renders child components
- MBOM BOM view exposes `Return to Source Part`
- where-used stays boundary-limited with explicit copy

## Non-Goals

- no Metasheet adapter changes
- no Wave 2 pact expansion
- no routing or baseline first-class drilldown
- no backend schema or API additions
