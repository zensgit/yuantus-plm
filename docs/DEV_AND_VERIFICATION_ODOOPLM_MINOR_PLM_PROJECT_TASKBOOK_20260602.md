# DEV & Verification: OdooPLM Minor Gap — `plm_project` Grounding/Right-Sizing Taskbook

Date: 2026-06-02

Records the doc-only delivery of
`DEVELOPMENT_ODOOPLM_MINOR_PLM_PROJECT_TASKBOOK_20260602.md` — the grounding +
right-sizing for the last OdooPLM minor gap (`plm_project`). Doc-only: no code;
authorizes no implementation. Baseline `main = 2873432e` (after finishing/
treatment R1 #690).

## 1. What changed

- New `plm_project` grounding/right-sizing taskbook: honest finding **DEFER**
  (no code-closable minor slice — Yuantus has no project subsystem), with the
  property-tag v0 **explicitly rejected**, two gated paths (native PM subsystem /
  outbound PM integration) each with a **promotion trip-wire**, and a closeout-
  ledger supersession that **exhausts the OdooPLM minor-gap line**.
- This DEV/verification record.
- Two sorted `DELIVERY_DOC_INDEX.md` entries (under `## Development &
  Verification`).

## 2. Grounding (against `main = 2873432e`)

- **No project subsystem** (verified negatives): no `class Project` /
  `__tablename__` project entity and **no `project_id` Column** anywhere in
  `src/yuantus` (repo-wide sweep empty); no PLM-object project linkage, no project
  router/service/ItemType.
- The `project` references that DO exist are **all incidental**: a
  `ProjectDemoSeeder`; the **JIRA** `project_key` in
  `parallel_tasks_service.py:5533` (external ticketing); and a `project_id`
  **form/payload string** on the CAD-preview upload endpoint
  (`api/routers/cad_preview.py:111` + `web/cad_preview.html:485`) — opaque
  passthrough metadata, not a PLM project. So the comparison's "`project`→3 文件"
  is incidental, not a partial subsystem.

## 3. Locked decisions (summary)

`plm_project` = Odoo-project integration; closing it = either a major native PM
subsystem (out of minor-gap scope; the PM-creep #689 warned of) or an outbound
PM-integration contract (externally-gated on a concrete target). There is **no
honest small R1**; a `project`-tag property is **rejected** because
`Item.properties` already stores arbitrary keys (ships nothing while implying a
non-existent feature). **Recommendation: defer**, promoting only on (A) a product
decision to own native PM → a separate program plan, or (B) a concrete external
PM target → an outbound contract behind a G2-style registry seam. This
**supersedes the #688 closeout's `plm_project` row** and exhausts the minor-gap
line.

## 4. Verification (this doc-only PR)

- doc-contract pytests — delivery-doc-index references; `## Development &
  Verification` sorting + completeness; doc-index sorting — pass.
- `verify_lisp_shell_static.py` 28, `verify_bridge_static.py` 13,
  `verify_material_sync_static.py` — pass (unchanged; no client/helper change).
- `git diff --check` clean.

## 5. Status

Doc-only grounding + right-sizing. There is **no implementation to opt into**;
the gap is deferred with explicit promotion trip-wires. With this, the OdooPLM
minor-gap line is closed; further OdooPLM work is externally-gated (G1/G6) or a
signal-driven Path-A/Path-B opt-in.
