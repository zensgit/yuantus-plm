# DEV_AND_VERIFICATION_SCHEDULER_BOM_TO_MBOM_HANDLER_20260421

日期：2026-04-21

## 1. Goal

Close the next bounded part of gap analysis `§一.5 BOM→MBOM 自动化 + 日期生效调度` by adding the first scheduler-driven BOM→MBOM business consumer.

This increment is intentionally narrow:

- add a scheduler task type: `bom_to_mbom_sync`;
- enqueue it through the existing lightweight scheduler / `meta_conversion_jobs` path;
- execute it through the existing worker handler registry;
- delegate MBOM creation to `MBOMService.create_mbom_from_ebom()`;
- keep the task default-off and source allowlist-driven.

## 2. Scope

Changed:

- `src/yuantus/config/settings.py`
- `src/yuantus/meta_engine/services/scheduler_service.py`
- `src/yuantus/meta_engine/tasks/scheduler_tasks.py`
- `src/yuantus/cli.py`
- `docker-compose.yml`
- `src/yuantus/meta_engine/tests/test_scheduler_service.py`
- `src/yuantus/meta_engine/tests/test_scheduler_compose_service_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md`

Not changed:

- no schema or migration;
- no router contract changes;
- no release orchestration schema changes;
- no full MBOM effectivity/date scheduler;
- no shared-dev 142 scheduler activation;
- no production scheduler activation;
- no broad scan of all `Part` items.

## 3. Safety Model

The new task is default-off at two levels:

| Layer | Default |
| --- | --- |
| global scheduler | `SCHEDULER_ENABLED=false` |
| BOM→MBOM task | `SCHEDULER_BOM_TO_MBOM_ENABLED=false` |

Even when explicitly enabled, the handler is allowlist-driven:

- it only processes payload/settings-provided `source_item_ids`;
- with no `source_item_ids`, it returns `skipped=true` and `reason=no_source_item_ids`;
- it requires `Part` source items;
- it requires `is_current=True`;
- it requires `state=Released` by default;
- it skips when an MBOM already exists for the source item.

This avoids accidental conversion of every Part in shared-dev or production.

## 4. Configuration

New settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `SCHEDULER_BOM_TO_MBOM_ENABLED` | `false` | Enable the periodic task |
| `SCHEDULER_BOM_TO_MBOM_INTERVAL_SECONDS` | `3600` | Minimum enqueue interval |
| `SCHEDULER_BOM_TO_MBOM_PRIORITY` | `85` | Job priority |
| `SCHEDULER_BOM_TO_MBOM_MAX_ATTEMPTS` | `1` | Job attempts |
| `SCHEDULER_BOM_TO_MBOM_SOURCE_ITEM_IDS` | empty | Comma-separated source Part IDs |
| `SCHEDULER_BOM_TO_MBOM_PLANT_CODE` | empty | Optional plant code on created MBOMs |

`docker-compose.yml` exposes the same env vars, with the task still default disabled.

## 5. Handler Contract

Task type:

```text
bom_to_mbom_sync
```

Minimal payload:

```json
{
  "source_item_ids": ["part-1"],
  "user_id": 1
}
```

Optional payload:

```json
{
  "source_item_ids": "part-1,part-2",
  "plant_code": "PLANT-1",
  "version": "1.0",
  "effective_from": "2026-04-21T00:00:00",
  "require_released": true,
  "transformation_rules": {
    "collapse_phantom": true
  }
}
```

Result shape:

```json
{
  "ok": true,
  "task": "bom_to_mbom_sync",
  "created": 1,
  "skipped_count": 0,
  "errors": [],
  "items": [
    {
      "source_item_id": "part-1",
      "mbom_id": "mbom-1",
      "name": "MBOM P-001"
    }
  ],
  "skipped_items": []
}
```

## 6. Implementation Notes

The scheduler registry adds `bom_to_mbom_sync` after `eco_approval_escalation` and `audit_retention_prune`.

The worker registry imports and registers:

```python
w.register_handler("bom_to_mbom_sync", bom_to_mbom_sync)
```

The handler deliberately uses the newer manufacturing service:

```python
MBOMService(session).create_mbom_from_ebom(...)
```

It does not call the older `/api/v1/bom/convert/ebom-to-mbom` path or `BOMConversionService.convert_ebom_to_mbom()`, because `§一.5` is about manufacturing MBOM resources and release-readiness integration, not cloning Engineering `Part` trees into `Manufacturing Part` items.

## 7. Verification

Focused scheduler tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_scheduler_compose_service_contracts.py
```

Observed:

```text
21 passed, 1 warning
```

The warning is the existing relationship model deprecation emitted by bootstrap import.

Adjacent scheduler / MBOM / release-orchestration / doc-index verification:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_scheduler_compose_service_contracts.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_release.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py \
  src/yuantus/meta_engine/tests/test_release_orchestration_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed:

```text
44 passed, 1 warning
```

`YUANTUS_AUTH_MODE=optional` is required for the local release-orchestration router tests in this checkout; without it those existing tests return 401 under the local `.env` auth settings.

Static checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/scheduler_service.py \
  src/yuantus/meta_engine/tasks/scheduler_tasks.py \
  src/yuantus/cli.py

git diff --check
```

Broader scheduler contract regression:

```bash
YUANTUS_AUTH_MODE=optional \
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_scheduler_compose_service_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_dry_run_preflight_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_audit_retention_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_eco_escalation_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_jobs_api_readback_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_report_contracts.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_release.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py \
  src/yuantus/meta_engine/tests/test_release_orchestration_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed:

```text
56 passed, 1 warning
```

## 8. Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Scheduler registry includes `bom_to_mbom_sync` | Pass |
| Task defaults disabled | Pass |
| Task payload reads source allowlist from settings | Pass |
| Worker registers `bom_to_mbom_sync` | Pass |
| Handler no-ops without source IDs | Pass |
| Handler creates MBOM for released current Part | Pass |
| Handler skips draft Part by default | Pass |
| Handler skips when MBOM already exists | Pass |
| Compose exposes task toggles with default disabled | Pass |
| No schema/router/API contract change | Pass |

## 9. Shared-Dev 142 Boundary

This PR does not run scheduler on shared-dev `142`.

Shared-dev verification remains read-only/no-op only. A future 142 activation would require a separate explicit decision, a source allowlist, and its own evidence pack.

## 10. Next Increment

After this handler is merged, the next bounded step should be a local activation smoke similar to the existing scheduler activation scripts:

- seed a released Part with a small EBOM;
- run scheduler dry-run;
- enqueue only `bom_to_mbom_sync`;
- run one worker;
- assert one `ManufacturingBOM` and MBOM lines are created;
- keep shared-dev default-off.
