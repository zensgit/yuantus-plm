# YuantusPLM Next-Cycle Implementation Plan (2026-04-26)

> **Nature of this document**: a planning artifact, not a sprint commitment.
> Documents how forward motion would proceed *if* the user chooses to trigger
> any of Phases 1–6. The "no-go pending external trigger" stance recorded in
> `DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` (PR #401) remains
> in effect until the user explicitly opts in to a phase below.

## 1. Goal & Scope

Provide a detailed, executable plan for closing the remaining `DEVELOPMENT_PLAN.md`
S6/S7 gaps and the `DEVELOPMENT_DESIGN.md` §11 Roadmap items, plus the
technical-debt cleanup of the 10 zero-route compatibility shells left behind
by the recent router decomposition cycle.

This MD is bounded:

- **In scope**: technical-debt cleanup, observability, multi-tenant Postgres
  hardening, search incremental + reports, tenant provisioning + backup
  runbook, external-service circuit breakers.
- **Out of scope** (deferred to trigger-gated taskbooks): scheduler production
  rehearsal, real CAD parsers (DWG/DXF/SW/Inventor/NX/CATIA), UI work
  (BOM Diff / CAD Viewer / approvals), MES/Routing/NCR/CAPA, shared-dev `142`
  readonly rerun, MES/sales/procurement business-scope expansion.

Each phase below maps to a sequence of bounded ~1–3 day PRs. No phase is
auto-triggered; each requires explicit user opt-in.

## 2. Inputs / Assumed Prior Reading

- `docs/DEVELOPMENT_PLAN.md` — canonical S0–S7 sprint plan
- `docs/DEVELOPMENT_DESIGN.md` — architecture + §11 Roadmap
- `docs/DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` — current backlog state + priority ordering
- `docs/DEV_AND_VERIFICATION_NEXT_CYCLE_CLOSEOUT_AND_REMAINING_WORK_20260423.md` — prior cycle closeout
- `docs/DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md` — doc-index atomicity rule

## 3. Current State Assessment

| Sprint / Roadmap | Status | Gap to address in this plan |
| --- | --- | --- |
| S0 工程底座 | ✅ Done | — |
| S1 Meta + RBAC | ✅ Done | — |
| S2 文件与文档 | ✅ Done | — |
| S3 BOM + Version | ✅ Done | — |
| S4 ECO/Workflow | ✅ Done | — |
| S5 CAD MVP | ✅ Done | (deferred: real CAD parsers) |
| S6 搜索/索引 | 🟡 Partial | Phase 4 (incremental + reports) |
| S7 私有化 + 多租户 | 🟡 Partial | Phase 3 (Postgres tenancy), Phase 5 (provisioning + backup) |
| Roadmap §11 可观测 | ❌ Gap | Phase 2 (structured logging + metrics), Phase 6 (circuit breakers) |
| 技术债：10 个 router shells | ❌ Tech debt | Phase 1 |

Concrete code-level findings supporting the assessment:

- 10 router shells still imported by `src/yuantus/api/app.py` despite owning
  zero `@router.*` decorators: `bom_router` (3 LOC), `eco_router` (10 LOC,
  re-export shim), `version_router` (6 LOC), `quality_router` (6 LOC),
  `box_router` (7 LOC), `cutted_parts_router` (7 LOC), `maintenance_router`
  (6 LOC), `subcontracting_router` (6 LOC), `document_sync_router` (23 LOC),
  `report_router` (5 LOC). Each is referenced by 1–4 test files (~30 test
  refs total).
- `src/yuantus/meta_engine/services/search_service.py` already supports
  Elasticsearch with DB fallback (`engine="elasticsearch"|"db"`); the
  pluggability is real. Gap is incremental indexing + reports/RPC aggregation.
- `src/yuantus/config/settings.py` exposes `TENANCY_MODE` ∈
  `{single, db-per-tenant, db-per-tenant-org}`, all sqlite-driven. Postgres
  schema-per-tenant is not implemented; design doc §3.2 explicitly calls it out
  as "未来如使用 Postgres，可改为 schema-per-tenant 或独立库".
- `src/yuantus/security/auth/quota_service.py` exists; quota model groundwork is in place but no provisioning API consumes it yet.
- `src/yuantus/api/middleware/` has `audit.py`, `auth_enforce.py`, `context.py`.
  No `structlog`, no `logger.bind`, no Prometheus exporter — observability
  foundation needs to be added.
- `src/yuantus/integrations/cad_connectors/` has `base.py`, `builtin.py`,
  `registry.py`, `config_loader.py` — connector architecture exists, but
  real DWG/DXF/SW parsers are out of this plan's scope.

## 4. Development Scheme

### 4.1 Principles

1. **Bounded increments per PR** — each PR ~1–3 days, independently revertible.
2. **Test discipline** — every new public surface gets a contract test mirroring the existing patterns (`test_*_router_contracts.py`, etc.).
3. **Doc-index atomicity** — every new MD ships with its index entry in the same commit (per `DEV_AND_VERIFICATION_DOC_INDEX_CONTRACT_DISCIPLINE_20260426.md`).
4. **No service-layer redesign in this plan** — service signatures stable; behavior changes are bounded.
5. **Per-phase DEV_AND_VERIFICATION MD** — each phase ends with a closeout MD recording what shipped, focused-test results, and next-phase readiness.
6. **Modular monolith stays** — no microservice extraction in this plan.
7. **No shared state mutations** — `.claude/`, `local-dev-env/`, shared-dev `142`, production scheduler all stay untouched.

### 4.2 Phase Ordering Rationale

Phases are ordered by:

- **Risk**: low → high (cleanup before schema migration before cross-cutting middleware).
- **Dependency**: independent items first (Phase 1 has zero dependencies on others).
- **Sprint mapping**: Phase 1 closes router-decomposition tail; Phases 2–3 unblock production deployment; Phases 4–5 close S6/S7; Phase 6 hardens external integrations.
- **Reversibility**: each phase can be paused/cancelled without blocking the next, except (Phase 3 ⇒ Phase 5) where tenant provisioning depends on schema-per-tenant existing.

### 4.3 Definition of Done (per PR)

- Affected family-specific contract tests pass.
- Doc-index trio (`completeness` + `sorting` + `references`) passes.
- DEV_AND_VERIFICATION MD merged with the PR.
- Pact provider verified if any public-route surface changed.
- `git diff --check` clean.
- `.claude/` and `local-dev-env/` not staged.

### 4.4 Definition of Done (per Phase)

- All PRs in the phase merged on `main`.
- Phase closeout DEV_AND_VERIFICATION MD documenting:
  - what shipped per sub-PR;
  - focused regression result snapshot;
  - acceptance criteria satisfied;
  - readiness check for the next phase.
- `bash scripts/verify_odoo18_plm_stack.sh full` green.
- All router decomposition closeout contracts green.

## 5. Phase 1 — Compatibility-Shell Cleanup (Tech Debt)

**Goal**: Finish the router-decomposition cycle by removing the 10 zero-route compatibility shells from `src/yuantus/api/app.py` (and optionally deleting the shell modules entirely once we confirm no plugin code imports them).

**Trigger**: engineering judgment; "codebase cleanup priority elevated explicitly" per the backlog triage. Does NOT need an external customer/ops trigger.

**Total effort**: ~3–5 engineering days across 10 sub-PRs.

**Current shell state in `src/yuantus/api/app.py` (verified at HEAD `e4ec310`):**

9 of the 10 shells are still **both** imported AND registered in app.py. `eco_router` is the lone exception — it is NOT imported by app.py at all (it is a re-export shim of `eco_core_router`, used only by test files). Each Phase 1 sub-PR for a "standard" shell must remove **both** lines, not just the import.

> **Recipe-correctness note**: an earlier draft of this section incorrectly claimed the `app.include_router(<shell>_router, …)` lines were already removed by a prior unregistration cycle. That was true only for `file_router` (PR #387) and `approvals_router` (commit `55ffae4`). The 9 standard shells listed below still have both lines present and must remove both.

**Sub-PRs (in increasing-difficulty order):**

| Sub-PR | Shell | Shell-module LOC | app.py import line | app.py `include_router` line | Test refs | Branch | Effort |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| P1.1 | `report_router` | 5 | 157 | 387 | 2 | `closeout/report-router-shell-removal-20260426` | 0.3 day |
| P1.2 | `quality_router` | 6 | 183 | 411 | 3 | `closeout/quality-router-shell-removal-2026MMDD` | 0.3 day |
| P1.3 | `maintenance_router` | 6 | 179 | 407 | 3 | `closeout/maintenance-router-shell-removal-2026MMDD` | 0.3 day |
| P1.4 | `subcontracting_router` | 6 | 194 | 416 | 3 | `closeout/subcontracting-router-shell-removal-2026MMDD` | 0.3 day |
| P1.5 | `version_router` | 6 | 201 | 379 | 4 | `closeout/version-router-shell-removal-2026MMDD` | 0.4 day |
| P1.6 | `box_router` | 7 | 44 | 315 | 3 | `closeout/box-router-shell-removal-2026MMDD` | 0.3 day |
| P1.7 | `cutted_parts_router` | 7 | 59 | 334 | 3 | `closeout/cutted-parts-router-shell-removal-2026MMDD` | 0.3 day |
| P1.8 | `bom_router` | 3 | 32 | 304 | 3 | `closeout/bom-router-shell-removal-2026MMDD` | 0.3 day |
| P1.9 | `eco_router` (re-export shim) | 10 | — (not imported by app.py) | — | 1 | `closeout/eco-router-shell-removal-2026MMDD` | 0.4 day |
| P1.10 | `document_sync_router` | 23 | 109 | 358 | 3 | `closeout/document-sync-router-shell-removal-2026MMDD` | 0.5 day |
| P1.11 | Phase 1 closeout MD + portfolio contract update | — | — | — | — | `closeout/phase-1-shell-cleanup-closeout-2026MMDD` | 0.3 day |

> Line numbers are baseline indicators on `e4ec310`; they may drift as earlier sub-PRs in this phase land. Each sub-PR must re-verify both line types via `grep -nE "from yuantus\.meta_engine\.web\.<shell> import <shell>\b" src/yuantus/api/app.py` and `grep -nE "app\.include_router\(<shell>," src/yuantus/api/app.py` before editing.

**Per-PR mechanical recipe (standard shells P1.1 – P1.8, P1.10):**

1. `git checkout -b <branch> origin/main`.
2. Confirm both target lines exist in `src/yuantus/api/app.py`:
   ```bash
   grep -nE "from yuantus\.meta_engine\.web\.<shell> import <shell>\b" src/yuantus/api/app.py
   grep -nE "app\.include_router\(<shell>," src/yuantus/api/app.py
   ```
   Both must print exactly one match before this PR proceeds.
3. **Remove BOTH lines from `src/yuantus/api/app.py`:**
   - the `from yuantus.meta_engine.web.<shell>_router import <shell>_router` import line, AND
   - the `app.include_router(<shell>_router, prefix="/api/v1")` registration line.
4. Run `python -c "from yuantus.api.app import create_app; create_app()"` to confirm the app boots without `ModuleNotFoundError` or registration loss.
5. Update each test file referencing the shell. Prefer migrating the test to the actual owner router (e.g., `test_report_router_permissions.py` references → use `report_dashboard_router` / `report_definition_router` / `report_saved_search_router` / `report_summary_search_router` per the route's actual owner).
6. Update `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py` to set the shell's entry to `imported_in_app: False` and `registered_in_app: False` (or remove the entry entirely if the shell module is deleted).
7. (Optional, only if `grep -rn "from yuantus\.meta_engine\.web\.<shell>" src/ docs/ scripts/ playwright/` confirms no other importers): delete `src/yuantus/meta_engine/web/<shell>_router.py`.
8. Run focused regression: family-specific contract tests + portfolio + doc-index trio.
9. PR + DEV_AND_VERIFICATION MD recording the change.

**Per-PR mechanical recipe (P1.9 — `eco_router` re-export shim, special case):**

`eco_router.py` is a re-export of `eco_core_router as eco_router` and is NOT imported by `app.py`. It is referenced only by tests. The recipe is therefore narrower:

1. `git checkout -b closeout/eco-router-shell-removal-2026MMDD origin/main`.
2. Confirm `app.py` does not contain `from yuantus.meta_engine.web.eco_router` or `app.include_router(eco_router,` (i.e., this is a re-export shim only — no app.py edits).
3. Update each test file that imports `yuantus.meta_engine.web.eco_router` or aliases `eco_router_module` to point at `eco_core_router` directly.
4. Update `test_router_decomposition_portfolio_contracts.py` to mark `eco_router` as a "shim, not registered in app".
5. (Optional) delete `src/yuantus/meta_engine/web/eco_router.py` after grepping all of `src/`, `docs/`, `scripts/`, `playwright/` for residual imports.
6. Run focused regression + boot check (step 4 of the standard recipe still applies as a safety net).
7. PR + DEV_AND_VERIFICATION MD.

**Acceptance criteria (Phase 1 as a whole):**

- `src/yuantus/api/app.py` has zero `from yuantus.meta_engine.web.<X>_router import <X>_router` import lines for any of: `bom_router`, `eco_router`, `version_router`, `quality_router`, `box_router`, `cutted_parts_router`, `maintenance_router`, `subcontracting_router`, `document_sync_router`, `report_router`.
- `src/yuantus/api/app.py` has zero `app.include_router(<X>_router, prefix="/api/v1")` registration lines for any of those shells.
- `python -c "from yuantus.api.app import create_app; create_app()"` boots cleanly.
- All decomposition closeout contracts updated and green (in particular: `test_router_decomposition_portfolio_contracts.py`).
- Previously-passing tests still pass; family-specific tests now resolve their `patch(...)` targets to the actual owner routers, not the shells.
- Phase 1 closeout MD merged with focused regression record.

**Risk**: Low–Medium — mechanical, but the prior recipe-bug (claiming the registrations were already gone) demonstrates that careless removal can break `create_app()`. Worst case: a plugin imports a shell directly, surfaced as a `ModuleNotFoundError` during `create_app()` → reverted by adding the shell back.

**Mitigation**:
- Each sub-PR is independently revertible.
- The boot-check command in step 4 of the recipe is a hard gate.
- Shell module file can stay (just unimport + unregister from app.py) if any external plugin reference is uncertain — preserves the import path even if `app.py` no longer wires it.
- The portfolio contract test (`test_router_decomposition_portfolio_contracts.py`) runs in CI on every PR and asserts the import + registration map; a missed-removal would surface there.

## 6. Phase 2 — Observability Foundation (Roadmap §11)

**Goal**: Add structured logging + job metrics so any production deployment is debuggable.

**Trigger**: production-readiness path; or any reported on-call incident where missing structured logs were the bottleneck.

**Total effort**: ~3–5 days across 3 sub-PRs.

**Sub-PRs:**

| Sub-PR | Scope | Branch | Effort |
| --- | --- | --- | ---: |
| P2.1 | Structured logging middleware (request_id + tenant_id + org_id + user_id + job_id + trace_id) using `structlog` or stdlib `logging` JSON formatter; all middleware emits via the same logger | `feat/observability-structured-logging-2026MMDD` | 1.5 days |
| P2.2 | Job metrics: success/failure/duration per `task_type`, exposed at `GET /api/v1/metrics` (Prometheus text format) or to stdout if `YUANTUS_METRICS_BACKEND=stdout` | `feat/observability-job-metrics-2026MMDD` | 1.5 days |
| P2.3 | Phase 2 closeout MD + contract tests asserting: logging fields present in audit/auth/context middleware; metrics endpoint registered; metrics present after job execution | `feat/observability-phase2-closeout-2026MMDD` | 0.5 day |

**Acceptance criteria:**

- Every API request log line contains: `request_id`, `tenant_id`, `org_id`, `user_id`, `path`, `method`, `status_code`, `latency_ms`.
- Every job lifecycle event emits a metric with `task_type`, `status`, `duration_ms`.
- `RUNBOOK_RUNTIME.md` updated with the field schema.
- New contract tests guard the field set (regression-prevention for future middleware refactors).

**Risk**: Medium — touches all middleware path; log-format changes risk breaking external log consumers if any.

**Mitigation**: backwards-compatible field names; opt-in flag `YUANTUS_LOG_FORMAT=json|text` defaulting to current behavior; structured-only mode behind feature flag for first deploy.

## 7. Phase 3 — Postgres Schema-per-Tenant (S7)

**Goal**: Production-grade tenancy isolation in Postgres mode, addressing
`DEVELOPMENT_DESIGN.md` §3.2 explicit follow-up.

**Trigger**: production deployment plan with Postgres backend; OR specific
tenant-isolation contract gap surfaced by a security review.

**Total effort**: ~5–7 days across 4 sub-PRs.

**Sub-PRs:**

| Sub-PR | Scope | Branch | Effort |
| --- | --- | --- | ---: |
| P3.1 | Design doc + alembic migration strategy MD: how schema-per-tenant maps to existing tables; how `db-per-tenant` migrates to `schema-per-tenant`; how alembic identifies the target schema; transactional concerns | `design/schema-per-tenant-strategy-2026MMDD` | 1 day |
| P3.2 | `TENANCY_MODE=schema-per-tenant` code path: `resolve_database_url` → schema name; SQLAlchemy `schema=` overrides; per-tenant `search_path` configuration | `feat/tenancy-schema-per-tenant-impl-2026MMDD` | 2 days |
| P3.3 | Migration upgrade path from existing `db-per-tenant` sqlite to Postgres schema-per-tenant: data export + transform + import; rollback plan; test on a copy | `feat/tenancy-migration-upgrade-2026MMDD` | 1.5 days |
| P3.4 | Multi-tenant isolation contract test: `tenantA` writes don't appear in `tenantB` queries; provisioning-API races covered | `test/tenancy-isolation-contracts-2026MMDD` | 1 day |
| P3.5 | Phase 3 closeout MD | `feat/tenancy-phase3-closeout-2026MMDD` | 0.5 day |

**Acceptance criteria:**

- `TENANCY_MODE=schema-per-tenant` works end-to-end with Postgres.
- `verify_multitenancy.sh` script exists and passes (per `DEVELOPMENT_PLAN.md` Appendix A row 7).
- Existing `single` and `db-per-tenant` modes continue to work (no regression).
- Migration script documented and tested on a non-production Postgres instance.

**Risk**: High — schema migrations affect every table; misalignment between alembic and runtime can corrupt or duplicate data.

**Mitigation**:
- Pilot on dev DB first.
- Hard-required code review step before P3.3 lands.
- Alembic revert plan included in P3.1.
- Phase 3 is the only phase with a formal "stop and reassess" gate after P3.2 before P3.3 starts.

## 8. Phase 4 — Search Incremental + Reports (S6)

**Goal**: Close the two named S6 gaps in `DEVELOPMENT_PLAN.md`.

**Trigger**: search-freshness pain (e.g., reported lag between Item creation
and search visibility); OR explicit S6 closure prioritization.

**Total effort**: ~3–5 days across 3 sub-PRs.

**Sub-PRs:**

| Sub-PR | Scope | Branch | Effort |
| --- | --- | --- | ---: |
| P4.1 | Outbox or job-based incremental indexing for Item/Doc/File/BOM mutations; lag monitoring | `feat/search-incremental-index-2026MMDD` | 2 days |
| P4.2 | Reports/RPC: aggregation by ItemType / state / ECO stage; export to CSV/JSON | `feat/search-reports-aggregation-2026MMDD` | 1.5 days |
| P4.3 | Phase 4 closeout MD + contract tests | `feat/search-phase4-closeout-2026MMDD` | 0.5 day |

**Acceptance criteria:**

- Search after Item create reflects new data within N seconds (N to be set by P4.1).
- Reports endpoint returns aggregations matching synthetic test data.
- No regression in existing search endpoints.

**Risk**: Medium — touches outbox or job worker lifecycle; index lag could
cause user-visible inconsistency if not monitored.

**Mitigation**: late-arrival reconciliation scan (background job that
re-indexes any lagging Item); freshness check exposed at `GET /api/v1/search/status`.

## 9. Phase 5 — Tenant/Org Provisioning + Backup Runbook (S7)

**Goal**: Close remaining S7 gaps.

**Trigger**: SaaS-readiness path; OR private-delivery deployment that needs
backup/restore drill.

**Total effort**: ~3–4 days across 3 sub-PRs.

**Sub-PRs:**

| Sub-PR | Scope | Branch | Effort |
| --- | --- | --- | ---: |
| P5.1 | Tenant/Org provisioning API: `POST /api/v1/admin/tenants`, `POST /api/v1/admin/tenants/{id}/orgs`, `POST /api/v1/admin/tenants/{id}/disable`; soft-quota application via `quota_service.py`; admin auth required | `feat/tenant-provisioning-api-2026MMDD` | 1.5 days |
| P5.2 | Backup/restore runbook + script: DB (Postgres `pg_dump`) + S3 (`mc mirror` or boto3); restore drill; documented in `RUNBOOK_BACKUP_RESTORE.md` | `feat/backup-restore-runbook-2026MMDD` | 1.5 days |
| P5.3 | Phase 5 closeout MD + tenant lifecycle acceptance test | `feat/provisioning-phase5-closeout-2026MMDD` | 0.5 day |

**Dependency**: P5.1 depends on Phase 3 if `schema-per-tenant` is the target; otherwise can use existing `db-per-tenant`. Recommend not starting P5 until Phase 3 closes.

**Acceptance criteria:**

- Provisioning API creates tenant/org with correct quota defaults.
- Disabling a tenant blocks new writes but preserves data.
- Backup script restores DB+S3 to a clean environment matching pre-backup state (data-equality check).
- `RUNBOOK_BACKUP_RESTORE.md` documents one-command and step-by-step paths.

**Risk**: Medium — provisioning has cross-cutting concerns (auth, audit,
quotas); backup drill is operationally novel.

**Mitigation**: lock-based provisioning (DB advisory lock per tenant);
admin-only auth on provisioning endpoints; backup drill against dev DB before
documenting.

## 10. Phase 6 — External-Service Circuit Breakers (Roadmap §11)

**Goal**: External-service call resilience.

**Trigger**: external-service flakiness pain (e.g., dedup_vision down
cascading into job retries) OR production-readiness path completion.

**Total effort**: ~2–3 days across 4 sub-PRs.

**Sub-PRs:**

| Sub-PR | Scope | Branch | Effort |
| --- | --- | --- | ---: |
| P6.1 | Circuit breaker for `dedupcad-vision` client (open/half-open/closed states; exponential backoff; metrics) | `feat/circuit-breaker-dedup-vision-2026MMDD` | 0.5 day |
| P6.2 | Circuit breaker for `cad-ml-platform` client | `feat/circuit-breaker-cad-ml-2026MMDD` | 0.5 day |
| P6.3 | Circuit breaker for `Athena` client | `feat/circuit-breaker-athena-2026MMDD` | 0.5 day |
| P6.4 | Phase 6 closeout MD + RUNBOOK_JOBS_DIAG.md update; contract tests asserting circuit-breaker state observable | `feat/circuit-breaker-phase6-closeout-2026MMDD` | 0.5 day |

**Acceptance criteria:**

- External-service outages don't cascade to job-retry storms.
- Circuit-breaker state visible via metrics and `GET /api/v1/health/dependencies`.
- Documented thresholds in `RUNBOOK_JOBS_DIAG.md`.

**Risk**: Low–Medium — bounded changes per service; per-service rollout means
one PR's breakage doesn't block others.

**Mitigation**: feature flag per service; default to disabled (status-quo
behavior); enable per service after acceptance.

## 11. Trigger-Gated Items (Deferred Out of This Plan)

The following are **not** in this plan. Each requires its own taskbook and
external trigger:

| Item | Required trigger | Rough effort |
| --- | --- | ---: |
| D1. Scheduler production rehearsal | Pilot owner + pilot environment + monitoring/rollback owner | 2–5 days + ops window |
| D2. Real CAD parsers (DWG/DXF/SW/Inventor/NX/CATIA) | SDK licensing decision + parser-format priority | 1–4 weeks per format |
| D3. UI work (BOM Diff / CAD Viewer / approvals) | Customer or stakeholder pull signal | 1–3+ weeks per UI area |
| D4. MES/Quality expansion (Routing/NCR/CAPA/eSign) | Business scope and roadmap approval | Multi-cycle |
| D5. Shared-dev `142` readonly observation rerun | Explicit credentials + execution window | 0.5 day per run |

These items are documented in `DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` §4 and not duplicated here.

## 12. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Phase 1 shell removal breaks an unknown plugin importer | L | M | Per-shell PRs; `grep -r` confirmation before delete; revertible |
| R2 | Phase 2 log format conflicts with existing log consumers | L | M | Backwards-compatible field names; opt-in flag default-off |
| R3 | Phase 3 schema migration breaks existing tenants | M | H | Pilot on dev DB; alembic revert; stop-and-reassess after P3.2 |
| R4 | Phase 4 incremental index lags real data without notice | M | M | Freshness check + late-arrival reconciliation |
| R5 | Phase 5 provisioning API races with manual DB ops | L | H | Lock-based provisioning + CLI override |
| R6 | Phase 6 circuit breaker over-trips on transient blips | M | L | Tunable thresholds; per-service feature flag |
| R7 | Cross-phase test bleed (one phase regresses another) | L | M | Each PR has its own focused regression; phase closeout MD records full-suite snapshot |
| R8 | Plan drifts as code changes between phases | M | M | Phase closeout MD re-asserts current state and next-phase prerequisites |
| R9 | Reviewer fatigue across 30+ PRs | M | M | Each PR ≤ 1 day, ≤ 200 LOC where possible; phase closeout MD as natural pause point |

## 13. Verification Strategy

### 13.1 Per-PR

- `py_compile` on touched .py files
- Family-specific contract tests
- Doc-index trio (`completeness` + `sorting` + `references`)
- `git diff --check` clean
- Pact provider verifier if route surface changed

### 13.2 Per-Phase

- All sub-PRs merged on `main`
- Phase-scoped focused regression (the union of all PRs' focused tests)
- Phase closeout DEV_AND_VERIFICATION MD with verification record

### 13.3 Final (Across All Six Phases)

- `bash scripts/verify_odoo18_plm_stack.sh full` green
- All router decomposition closeout contracts green
- Pact provider full verification
- Single closeout MD: `DEV_AND_VERIFICATION_PRODUCTION_READINESS_FINAL_CLOSEOUT_<date>.md`

## 14. Working Agreement

- **Branch naming**: `<phase-prefix>/<scope>-<YYYYMMDD>` (e.g., `closeout/report-router-shell-removal-20260426`).
- **Commit messages**: imperative, ≤ 72-char subject, body explains the why.
- **PR titles**: match the commit subject after squash; reference parent phase MD in body.
- **PR bodies**: use the existing template (Summary / Test plan / Cross-references).
- **Review cadence**: Codex (or designated reviewer) reviews each PR; Claude addresses fix requests in same branch.
- **Pause points**: at the end of each phase, user must explicitly opt-in to the next phase. No phase auto-starts.
- **Cancel signal**: at any time, user can abort the active phase; the in-flight branch is closed and any partial work documented in a cancellation MD.

## 15. Files Changed (this PR only)

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` (this MD)
- `docs/DELIVERY_DOC_INDEX.md` (entry for this MD, alphabetically positioned
  immediately after `DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md`)

## 16. Verification (this PR)

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

Expected: 4 passed + clean.

## 17. Non-Goals (this PR)

- This PR delivers **only** the planning document. It does **not** implement any phase.
- No code, schema, runtime, CI, or contract changes.
- No retroactive edit of `DEVELOPMENT_PLAN.md` or `DEVELOPMENT_DESIGN.md` (they remain canonical for product scope).
- No `.claude/` or `local-dev-env/` files added.

## 18. Operating Mode After This PR

Per `DEV_AND_VERIFICATION_NEW_CYCLE_BACKLOG_TRIAGE_20260426.md` §9:

1. Keep `main` stable.
2. User decides whether to opt-in to Phase 1 (or any phase). Each opt-in starts the corresponding sub-PR sequence.
3. Phases proceed sequentially by default; parallelism is allowed only between Phase 1 and Phase 2 (no shared files), and between Phase 6 and Phase 5 (independent surfaces).
4. After each phase, re-evaluate priority before continuing — external signal may have shifted the order.
5. Terminate the implementation arc when (a) all 6 phases close, OR (b) external trigger redirects to a Category D item.
