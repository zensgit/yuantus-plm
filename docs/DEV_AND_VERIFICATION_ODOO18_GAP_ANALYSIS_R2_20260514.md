# DEV / Verification - Odoo18 Gap Analysis R2 - 2026-05-14

## 1. Goal

Record the docs-only R2 correction for
`docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`.

This revision hardens the Odoo18 PLM gap analysis against the current Yuantus
codebase. It does not introduce runtime behavior, migrations, settings, routes,
or feature flags.

## 2. Background

The first draft correctly widened the Odoo comparison surface beyond the 35
`plm_*` extensions, but it under-counted existing Yuantus implementation in the
Odoo18 parallel-task line.

The R2 update reclassifies capability status using four buckets:

- `Integrated`
- `Integrated but incomplete`
- `Prototype exists`
- `Absent`

This avoids treating existing models, routers, and services as missing features.

## 3. Code Evidence Incorporated

| Area | R2 correction | Code evidence |
| --- | --- | --- |
| ECO activity gates | No longer described as absent. ECO activity blockers already gate ECO transitions. | `src/yuantus/meta_engine/models/parallel_tasks.py`, `src/yuantus/meta_engine/services/eco_service.py` |
| Breakage/helpdesk | No longer described as absent. Breakage incident and helpdesk sync surfaces exist. | `src/yuantus/meta_engine/web/parallel_tasks_breakage_router.py` |
| Consumption variance | No longer described as absent. Consumption plans, records, and variance endpoint exist. | `src/yuantus/meta_engine/web/parallel_tasks_consumption_router.py` |
| Workflow actions | Reframed from missing automation to incomplete automation. Fixed action primitives exist, but generic DSL does not. | `src/yuantus/meta_engine/services/parallel_tasks_service.py` |
| Workorder documents | Reframed as version-lock gap, not missing workorder docs. | `src/yuantus/meta_engine/web/parallel_tasks_workorder_docs_router.py` |
| Quality/workorder | Reframed as runtime-enforcement gap. Routing and operation IDs already exist on quality points/checks. | `src/yuantus/meta_engine/quality/models.py` |
| Pack-and-go | Reframed as mainline/version-lock strategy. The plugin already exists. | `plugins/yuantus-pack-and-go/main.py` |
| CAD conversion | Reframed as multi-server pool/backpressure gap. Job-backed conversion already exists. | `src/yuantus/meta_engine/web/file_conversion_router.py` |

## 4. LOC Correction

R2 removes the misleading `ECO service 121K lines` claim.

Measured reference:

```bash
wc -l src/yuantus/meta_engine/services/eco_service.py
```

Result at review time:

```text
3199 src/yuantus/meta_engine/services/eco_service.py
```

Other LOC values in the gap analysis are marked as dimensional references only,
not maturity proof.

## 5. Priority Change

R2 changes the recommended next-work ordering from "build missing domains" to
"close existing integration gaps first".

Recommended order:

1. `workorder version-lock`
2. `ECR intake domain`
3. `quality workorder runtime enforcement`
4. `pack-and-go mainline/version-lock hardening`
5. `CAD conversion multi-server pool`
6. `workflow automation event coverage / DSL evaluation`
7. `breakage to design feedback loop`
8. `consumption MES ingestion contract`
9. `maintenance to manufacturing bridge`

## 6. Non-Goals

This R2 document does not:

- start any new implementation phase,
- unblock Phase 3 cutover or Phase 5,
- authorize Odoo18 follow-up implementation,
- change runtime code,
- change CI,
- add migration files,
- add new API routes,
- mark any customer/operator gate complete.

Each candidate still requires independent taskbook approval before execution.

## 7. Files Changed

| File | Change |
| --- | --- |
| `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md` | New R2 gap-analysis document. |
| `docs/DEV_AND_VERIFICATION_ODOO18_GAP_ANALYSIS_R2_20260514.md` | This verification record. |
| `docs/DELIVERY_DOC_INDEX.md` | Adds index entries for the development analysis and this verification record. |

## 8. Verification Commands

Doc-index trio:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Whitespace check:

```bash
git diff --check
```

## 9. Verification Results

Local verification after indexing:

| Check | Result |
| --- | --- |
| Doc-index trio | `4 passed in 0.03s` |
| `git diff --check` | clean |

## 10. Closeout Decision

R2 is a docs-only correction. It is suitable to land with the current green
doc-index trio and clean whitespace check.
