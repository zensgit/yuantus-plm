# CAD BOM Operations Runbook

This runbook covers operator-facing diagnosis, export, review, and bounded
recovery for CAD BOM imports.

## 0. Preconditions

- Valid `$TOKEN`
- Known `file_id`
- Tenant and org headers available when auth is required

## 1. Read the derived CAD BOM surface

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

Expected meanings:

- `ready`: import is usable
- `degraded`: import exists but requires operator review
- `empty`: connector returned no usable BOM
- `missing`: no CAD BOM artifact or job result is available

## 2. Export an operator evidence bundle

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
- `summary.json`
- `review.json`
- `import_result.json`
- `bom.json`
- `history.json`
- `history.csv`
- `recovery_actions.csv`
- `issue_codes.csv`
- `README.txt`

Use this bundle for:

- operator handoff
- support/incident evidence
- regression attachment
- customer-facing private deployment verification

## 3. Check review status

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

## 4. Check CAD history

```bash
curl -s 'http://127.0.0.1:7910/api/v1/cad/files/<file_id>/history?limit=20' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'x-tenant-id: tenant-1' -H 'x-org-id: org-1'
```

Typical useful actions:

- `cad_bom_reimport_requested`
- `cad_review_update`
- other CAD pipeline audit entries already emitted for the file

## 5. Reimport with bounded recovery

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

## 6. Triage shortcuts by issue code

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

## 7. When to escalate

Escalate to a deeper connector/source investigation when:

- `summary.status` remains `degraded` after a clean reimport
- `issue_codes` change unexpectedly across repeated exports
- `history` shows repeated reimport requests without quality improvement
- the structured bundle contradicts the raw `/api/v1/file/<file_id>/cad_bom`
  artifact

For generic CAD job failures outside BOM import, also use:

- `docs/RUNBOOK_JOBS_DIAG.md`
