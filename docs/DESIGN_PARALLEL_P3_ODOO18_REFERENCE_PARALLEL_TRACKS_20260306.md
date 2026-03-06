# Parallel P3 Odoo18 Reference Mapping and Parallel Tracks (2026-03-06)

## 1. Objective

Use `references/odoo18-enterprise-main` as a reference baseline to define high-value parallel development tracks for Yuantus, with minimal-risk MVP slices.

## 2. Reference Modules Reviewed

- `addons/plm_breakages`
- `addons/plm_ent_breakages_helpdesk`
- `addons/plm_document_multi_site`
- `addons/plm_pack_and_go`
- `addons/plm/models/plm_checkout.py`
- `addons/plm_workflow_custom_action`
- `addons/plm_suspended`
- `addons/plm_compare_bom`
- `addons/plm_bom_summarize`
- `addons/plm_project`
- `addons/mirror_document_server`

## 3. Parallel Track A: Breakage/Helpdesk Operations

### A1. Breakage-Ticket bidirectional link and traceability

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_ent_breakages_helpdesk/models/breakages.py`
  - `references/odoo18-enterprise-main/addons/plm_ent_breakages_helpdesk/models/helpdesk_ticket.py`
- Borrowed idea: normalize many-to-many trace between breakage and ticket.
- Yuantus MVP:
  - enrich breakage-helpdesk sync payload and replay export with explicit linked-ticket list and latest ticket status summary.

### A2. Breakage rollup counters on BOM/MO scope

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_breakages/models/mrp_bom.py`
  - `references/odoo18-enterprise-main/addons/plm_breakages/models/mrp_production.py`
- Borrowed idea: computed breakage counters at structure/execution scope.
- Yuantus MVP:
  - add grouped counters by `bom_id`, `mbom_id`, `routing_id` in breakage cockpit aggregates.

### A3. Standardized breakage incident sequence

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_breakages/models/breakages.py`
- Borrowed idea: deterministic incident sequence assignment.
- Yuantus MVP:
  - add optional human-readable incident code in breakage exports and replay batches.

## 4. Parallel Track B: Doc-Sync and Checkout Governance

### B1. Sync-action queue model with per-site push/pull semantics

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_document_multi_site/models/plm_document_action_syncronize.py`
  - `references/odoo18-enterprise-main/addons/plm_document_multi_site/models/ir_attachment.py`
- Borrowed idea: explicit `pull/push` action queue and done-state tracking.
- Yuantus MVP:
  - classify replay jobs by transfer direction and site, include in trends/export dimensions.

### B2. Checkout gate on pending synchronization

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_document_multi_site/models/ir_attachment.py` (`canCheckOut`)
  - `references/odoo18-enterprise-main/addons/plm/models/plm_checkout.py`
- Borrowed idea: prevent checkout while synchronization is pending.
- Yuantus MVP:
  - strengthen version checkout gate with configurable strictness (`warn|block`) and per-site pending thresholds.

### B3. Mirror server compatibility adapter

- Reference:
  - `references/odoo18-enterprise-main/addons/mirror_document_server/main.py`
  - `references/odoo18-enterprise-main/addons/plm_document_multi_site/models/plm_remote_server.py`
- Borrowed idea: remote mirror upload/download/document existence checks.
- Yuantus MVP:
  - add adapter mode for BasicAuth mirror endpoints in remote site probe + replay worker.

## 5. Parallel Track C: ECO/Workflow/BOM Change Automation

### C1. Before/after workflow action hooks

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_workflow_custom_action/models/plm_automated_wf_actions.py`
  - `references/odoo18-enterprise-main/addons/plm_workflow_custom_action/models/product_template.py`
- Borrowed idea: state-transition hooks with dynamic actions and optional domain filtering.
- Yuantus MVP:
  - extend workflow custom action engine with richer predicates and action ordering policy.

### C2. Suspended state with explicit unsuspend path

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_suspended/models/ir_attachment.py`
  - `references/odoo18-enterprise-main/addons/plm_suspended/models/product_template.py`
- Borrowed idea: explicit suspended state blocks writable operations until unsuspend.
- Yuantus MVP:
  - add suspension gate to selected ECO/checkout operations with audit reason fields.

### C3. BOM compare with strategy modes + semi-auto reconciliation

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
- Borrowed idea: compare modes (`only_product`, `num_qty`, summarized) and guided update actions.
- Yuantus MVP:
  - expose compare mode switch in existing BOM-diff compute endpoint and add apply-preview safety checks.

### C4. BOM summarized propagation mode

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_bom_summarize/models/mrp_bom.py`
- Borrowed idea: context-driven summarized relation handling.
- Yuantus MVP:
  - optional summarize mode in BOM diff/export and ECO compute-changes path.

### C5. Project task chain driving PLM state progression

- Reference:
  - `references/odoo18-enterprise-main/addons/plm_project/models/project_task.py`
  - `references/odoo18-enterprise-main/addons/plm_project/models/mail_activity.py`
- Borrowed idea: task-chain completion triggers product workflow transition.
- Yuantus MVP:
  - map ECO activity completion chain to release readiness state updates with role checks.

## 6. Priority and Parallelization

### P0 (can start immediately in parallel)

1. B2 checkout gate strictness modes.
2. A2 breakage grouped counters.
3. C3 BOM compare mode switch.

### P1 (second wave)

1. B1 sync-action direction dimensions.
2. C1 workflow custom action predicate enhancement.
3. C2 suspension gate integration.

### P2 (third wave)

1. B3 mirror compatibility adapter.
2. C5 ECO-task-chain linkage.
3. A3 incident sequence normalization.

## 7. Risks and Constraints

- Odoo reference code includes patterns unsuitable for direct adoption (e.g., per-record manual commit, plaintext credentials).
- Data model semantics differ (`mrp.bom.line` vs Yuantus relationship-style lines), requiring translation layers.
- Any checkout/sync hard gate must remain tenant/site aware to avoid false blocks.
