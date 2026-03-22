# CAD BOM Operations Runbook

This runbook covers operator-facing diagnosis, export, review, and bounded
recovery for CAD BOM imports.

## 0. Preconditions

- Valid `$TOKEN`
- Known `file_id`
- Tenant and org headers available when auth is required

## 1. Read the unified CAD proof surface

Use the proof surface first when you need one revision-centered answer about
asset trust, viewer readiness, BOM drift, review, and next actions:

```bash
curl -s 'http://127.0.0.1:7910/api/v1/cad/files/<file_id>/proof?history_limit=20' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

Focus on:

- `operator_proof.status`
- `operator_proof.decision_status`
- `operator_proof.requires_operator_decision`
- `operator_proof.proof_gaps`
- `operator_proof.issue_codes`
- `operator_proof.next_actions`
- `active_decision`
- `asset_quality.status`
- `asset_quality.result.status`
- `viewer_readiness.viewer_mode`
- `cad_bom.summary.status`
- `cad_bom.mismatch.status`

Expected meanings:

- `ready`: current CAD asset, viewer, and BOM evidence is coherent enough for
  normal operator use
- `needs_review`: evidence exists, but drift/degradation/review gaps require
  operator attention
- `blocked`: the proof surface is missing critical evidence such as trustworthy
  asset output or viewer readiness

## 2. Record or inspect proof acknowledgement / waiver

Read decision trail:

```bash
curl -s 'http://127.0.0.1:7910/api/v1/cad/files/<file_id>/proof/decisions?history_limit=20' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

Record a bounded acknowledgement:

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/files/<file_id>/proof/decisions \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{
    "decision":"acknowledged",
    "scope":"full_proof",
    "comment":"accepted during staged rollout monitoring"
  }'
```

Record a bounded waiver:

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/files/<file_id>/proof/decisions \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{
    "decision":"waived",
    "scope":"full_proof",
    "comment":"accepted while downstream BOM catches up",
    "reason_code":"downstream_lag",
    "expires_at":"2026-03-29T12:00:00Z"
  }'
```

Focus on:

- `current_fingerprint`
- `active_decision`
- `entries[*].decision`
- `entries[*].scope`
- `entries[*].issue_codes`
- `entries[*].covers_current_proof`

Expected meanings:

- `decision_status=open`: proof 仍需 operator decision
- `decision_status=acknowledged`: 当前 proof 已被显式确认，但技术风险仍存在
- `decision_status=waived`: 当前 proof 已被带 reason 的 bounded waiver 覆盖
- `covers_current_proof=false`: 旧 decision 已不再覆盖最新 proof，需要重新确认

## 3. Read the derived CAD BOM surface

Use the structured operator surface first:

```bash
curl -s http://127.0.0.1:7910/api/v1/cad/files/<file_id>/bom \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

Focus on:

- `summary.status`
- `summary.issue_codes`
- `summary.recovery_actions`
- `summary.root` / `summary.root_source`
- `import_result.contract_validation`
- `mismatch.status`
- `mismatch.mismatch_groups`
- `mismatch.grouped_counters`

Expected meanings:

- `ready`: import is usable
- `degraded`: import exists but requires operator review
- `empty`: connector returned no usable BOM
- `missing`: no CAD BOM artifact or job result is available

## 4. Read the dedicated mismatch surface

Use the mismatch surface when you need to know whether the current derived CAD
BOM still matches the live BOM:

```bash
curl -s http://127.0.0.1:7910/api/v1/cad/files/<file_id>/bom/mismatch \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

Focus on:

- `status`
- `reason`
- `analysis_scope`
- `line_key`
- `grouped_counters`
- `mismatch_groups`
- `issue_codes`
- `recovery_actions`

Expected meanings:

- `match`: derived CAD BOM and live BOM align for the current compare key
- `mismatch`: drift exists and should be reviewed before recovery
- `unresolved`: comparison could not be completed, usually because item binding
  or root binding is missing
- `missing`: the CAD BOM payload is empty, so no live-vs-CAD mismatch analysis
  could be produced

## 5. Export an operator evidence bundle

JSON:

```bash
curl -s http://127.0.0.1:7910/api/v1/cad/files/<file_id>/bom/export?export_format=json \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

ZIP:

```bash
curl -L http://127.0.0.1:7910/api/v1/cad/files/<file_id>/bom/export?export_format=zip \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -o cad-bom-ops-<file_id>.zip
```

Bundle contents:

- `bundle.json`
- `file.json`
- `operator_proof.json`
- `active_decision.json`
- `proof_decisions.json`
- `proof_decisions.csv`
- `viewer_readiness.json`
- `asset_quality.json`
- `asset_quality_issue_codes.csv`
- `asset_quality_recovery_actions.csv`
- `summary.json`
- `review.json`
- `import_result.json`
- `bom.json`
- `mismatch.json`
- `live_bom.json`
- `history.json`
- `history.csv`
- `recovery_actions.csv`
- `issue_codes.csv`
- `mismatch_delta.csv`
- `mismatch_rows.csv`
- `mismatch_issue_codes.csv`
- `mismatch_recovery_actions.csv`
- `mismatch_delta_preview.json`
- `proof_manifest.json`
- `README.txt`

Use this bundle for:

- operator handoff
- support/incident evidence
- regression attachment
- customer-facing private deployment verification

Always export the bundle before applying recovery actions when
`operator_proof.status!=ready` or `mismatch.status=mismatch`.

## 6. Check review status

```bash
curl -s http://127.0.0.1:7910/api/v1/cad/files/<file_id>/review \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

Focus on:

- `state`
- `note`
- `reviewed_at`
- `reviewed_by_id`

If a partial or invalid import was produced by the async pipeline, the system
can automatically flip the file to `pending`.

## 7. Check CAD history

```bash
curl -s 'http://127.0.0.1:7910/api/v1/cad/files/<file_id>/history?limit=20' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

Typical useful actions:

- `cad_bom_reimport_requested`
- `cad_operator_proof_acknowledged`
- `cad_operator_proof_waived`
- `cad_review_update`
- other CAD pipeline audit entries already emitted for the file

## 8. Reimport with bounded recovery

If `summary.recovery_actions` indicates reimport is appropriate:

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/files/<file_id>/bom/reimport \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{}'
```

Optional explicit item binding:

```bash
curl -s -X POST http://127.0.0.1:7910/api/v1/cad/files/<file_id>/bom/reimport \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1' \
  -d '{"item_id":"<item_id>"}'
```

Common failure codes:

- `cad_bom_reimport_item_missing`
- `cad_bom_reimport_item_ambiguous`

## 9. Triage shortcuts by issue code

- `asset_quality_missing`
  - open `/proof` and confirm whether geometry/metadata evidence exists at all
- `asset_quality_degraded`
  - inspect `asset_quality.issue_codes` and `asset_quality_recovery_actions`
- `converter_result_failed`
  - inspect `asset_quality.result` and export the proof bundle before retrying
- `cad_bom_live_mismatch`
  - inspect `operator_proof.proof_gaps`, then `mismatch.grouped_counters`
- `cad_review_pending`
  - inspect `review.state` and `history` before accepting recovery
- `operator_proof.decision_status=open`
  - record an acknowledgement or waiver before handoff if the current proof is intentionally accepted
- `active_decision.covers_current_proof=false`
  - old acknowledgement no longer matches current proof; re-export and re-record a fresh decision

- `contract_invalid`
  - inspect `import_result.contract_validation`
  - export the bundle before changing anything
- `duplicate_node_ids`
  - correct connector/source node identity collisions
- `root_binding_invalid`
  - ensure a single assembly root is present
- `edge_reference_missing`
  - repair parent/child references
- `import_errors`
  - inspect connector/import errors before re-run
- `skipped_lines`
  - verify whether skipped relationships were expected
- `live_bom_structure_mismatch`
  - inspect `mismatch.grouped_counters.structure`
  - export the proof bundle before reimport
- `live_bom_quantity_mismatch`
  - inspect `mismatch.grouped_counters.quantity` and `mismatch_delta.csv`
  - review quantity/UOM drift before reimport

## 10. When to escalate

Escalate to a deeper connector/source investigation when:

- `summary.status` remains `degraded` after a clean reimport
- `operator_proof.status` remains `blocked` or `needs_review` after expected
  recovery actions
- `operator_proof.requires_operator_decision=true` and no responsible operator
  can record a decision
- `mismatch.status` remains `mismatch` after drift review and reimport
- `issue_codes` change unexpectedly across repeated exports
- `history` shows repeated reimport requests without quality improvement
- the structured bundle contradicts the raw `/api/v1/file/<file_id>/cad_bom`
  artifact

For generic CAD job failures outside BOM import, also use:

- `docs/RUNBOOK_JOBS_DIAG.md`
