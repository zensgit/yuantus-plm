# Scheduler Dry-Run Preflight Helper - Development And Verification

Date: 2026-04-21

## 1. Goal

Package the scheduler dry-run CLI into a repeatable evidence-producing helper:

- run `yuantus scheduler --once --dry-run`;
- capture `would_enqueue`, `skipped`, and `disabled` decisions;
- prove `meta_conversion_jobs` row count is unchanged;
- make shared-dev/prod DB targets explicit via `--allow-non-local-db`.

This is the operational wrapper for the scheduler dry-run capability delivered in `DEV_AND_VERIFICATION_SCHEDULER_DRY_RUN_PREFLIGHT_20260421.md`.

## 2. Delivered Files

- `scripts/run_scheduler_dry_run_preflight.sh`
- `src/yuantus/meta_engine/tests/test_scheduler_dry_run_preflight_contracts.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

## 3. Safety Model

Default:

```bash
bash scripts/run_scheduler_dry_run_preflight.sh
```

The helper defaults to:

- `sqlite:///<repo>/local-dev-env/data/yuantus.db`
- `TENANT=tenant-1`
- `ORG=org-1`
- `YUANTUS_TENANCY_MODE=disabled`
- `--force`, so globally disabled scheduler environments can still be evaluated without writes.

Guardrails:

- local SQLite DB is allowed only under `./local-dev-env/data`;
- non-local SQLite paths are refused unless `--allow-non-local-db` is set;
- non-SQLite DB URLs are refused unless `--allow-non-local-db` is set;
- worker is never invoked;
- validation fails if `enqueued` is non-empty;
- validation fails if `job_count_before != job_count_after`.

shared-dev/prod DB targets require `--allow-non-local-db`.

Contract anchor: shared-dev/prod DB targets require --allow-non-local-db.

## 4. Output Artifacts

The helper writes:

- `scheduler_dry_run.json`
- `job_counts.json`
- `validation.json`
- `README.txt`

Example validation:

```json
{
  "disabled_count": 0,
  "errors": [],
  "job_count_after": 1,
  "job_count_before": 1,
  "ok": true,
  "skipped_count": 0,
  "would_enqueue_count": 2
}
```

Example scheduler output summary:

```json
{
  "enqueued": [],
  "would_enqueue": [
    "eco_approval_escalation",
    "audit_retention_prune"
  ],
  "skipped": [],
  "disabled": []
}
```

## 5. Verification

Local preflight smoke:

```bash
bash scripts/run_scheduler_dry_run_preflight.sh \
  --output-dir ./tmp/scheduler-dry-run-preflight-20260421-141755
```

Observed:

- `validation.ok=true`
- `job_count_before=1`
- `job_count_after=1`
- `would_enqueue_count=2`
- `enqueued=[]`

Focused regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_dry_run_preflight_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_scheduler_audit_retention_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_eco_escalation_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Shell checks:

```bash
bash -n scripts/run_scheduler_dry_run_preflight.sh
scripts/run_scheduler_dry_run_preflight.sh --help
git diff --check
```

## 6. Boundary

This helper does not enable scheduler on shared-dev 142 or production.

It is the evidence collection step before a future scheduler enablement decision:

1. run P2 readonly observation;
2. run scheduler dry-run preflight;
3. review `would_enqueue` decisions;
4. decide whether a separate enablement PR is warranted.
