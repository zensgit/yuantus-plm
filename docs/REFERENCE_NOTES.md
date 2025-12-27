# Reference Notes (YuantusPLM)

## Scope

This note summarizes architecture and workflow ideas from reference codebases
and maps them to Yuantus modules. Use as inspiration only; do not copy code.
Some references are GPL/AGPL.

Sources reviewed:
- references/docdoku-plm
- references/erpnext
- references/odoo18-enterprise-main

## DocDokuPLM conversion service

Reference:
- references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/App.java
- references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/GeometryParser.java
- references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/Decimater.java

Pattern:
- Async conversion microservice (queue listener).
- Load file from vault, write to temp dir, run converter.
- Compute geometry bounding box and LODs.
- Send results back via API callback.
- Strong error handling + temp cleanup.

Yuantus mapping:
- CAD extractor microservice (separate service).
- Preview/geometry pipeline can reuse bounding box and LOD flow.
- Job payload should include correlation id for callback.

## ERPNext BOM diff (API)

Reference:
- references/erpnext/erpnext/manufacturing/doctype/bom/bom.py (get_bom_diff)

Pattern:
- Compare BOM header fields and child tables.
- Output: changed, added, removed, row_changed.
- Uses stable identifiers for child rows (item_code, operation, etc.).

Yuantus mapping:
- BOM Compare API should return:
  - header_changes: list of field changes
  - row_added, row_removed, row_changed
  - identifier keys for line comparison

## ERPNext BOM comparison UI

Reference:
- references/erpnext/erpnext/manufacturing/page/bom_comparison_tool/bom_comparison_tool.js

Pattern:
- One API call, then render grouped tables:
  - "Values Changed"
  - "Changes in Items/Operations"
  - "Rows Added/Removed"

Yuantus mapping:
- Keep the diff schema stable to enable UI grouping.
- Provide text labels for field display.

## Odoo BOM compare modes

Reference:
- references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py

Pattern:
- Three compare modes:
  - only_product: presence/absence by product id
  - summarized: aggregate quantities per product
  - num_qty: compare by product id + position + qty
- Emits reason: added, changed, changed_qty.

Yuantus mapping:
- Add compare_mode param to BOM diff API.
- Return reason per row change to drive UI highlighting.

## Odoo automated conversion stack

Reference:
- references/odoo18-enterprise-main/addons/plm_automated_convertion/models/plm_convert_stack.py
- references/odoo18-enterprise-main/addons/plm_automated_convertion/models/ir_attachment.py

Pattern:
- Conversion rules and servers.
- Stack of conversion tasks with status + error text.
- Supports internal conversion or HTTP external server.

Yuantus mapping:
- Add "conversion rule" model for CAD pipelines.
- Allow routing to external conversion servers.
- Persist conversion errors and retry policies.

## Odoo date-based BOM updates

Reference:
- references/odoo18-enterprise-main/addons/plm_date_bom/models/plm_temporary_date_compute.py
- references/odoo18-enterprise-main/addons/plm_date_bom/models/mrp_bom.py

Pattern:
- Detect obsolete components in BOMs.
- Update where-used for affected BOMs.
- Two workflows: update lines in place, or create new BOM.
- Cron jobs for periodic updates.

Yuantus mapping:
- Scheduled "obsolete scan" for BOM lines.
- Provide two actions:
  - update lines to latest released components
  - create new BOM revision with latest components
- Integrate with effectivity and versioning.

## DocDoku change and workflow model

Reference:
- references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-core/src/main/java/com/docdoku/plm/server/core/change
- references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-core/src/main/java/com/docdoku/plm/server/core/workflow

Pattern:
- Separate workflow definitions (models) from instances (workflows).
- Change entities (request/order/issue) link to workflows.
- Task model supports assignments and lifecycle states.

Yuantus mapping:
- ECO should maintain:
  - workflow_model (definition)
  - workflow_instance (runtime)
  - task assignments and states

## Suggested action items for Yuantus

- CAD extractor microservice:
  - queue-based jobs
  - temp file handling
  - callback to Yuantus API
  - optional bbox + LOD outputs
- BOM Compare API:
  - include compare_mode
  - return header and row-level diffs
  - reason codes for UI
- Obsolete BOM handling:
  - scheduled scan + update/revise paths
  - integrate effectivity rules
- Conversion server registry:
  - external conversion routing
  - error/ retry metadata
