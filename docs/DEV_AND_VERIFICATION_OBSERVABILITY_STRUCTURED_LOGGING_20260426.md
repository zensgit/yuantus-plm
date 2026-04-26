# DEV / Verification — Phase 2 P2.1 Observability Structured Logging (2026-04-26)

## 1. Goal

Phase 2 sub-PR **P2.1** of the next-cycle plan
(`docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md`, §6 — "Phase 2 — Observability
Foundation"): introduce a **`RequestLoggingMiddleware`** that emits one
structured log line per HTTP request, with a stable field schema
(`request_id`, `tenant_id`, `org_id`, `user_id`, `method`, `path`,
`status_code`, `latency_ms`).

Provide a feature flag (`LOG_FORMAT=text|json`) so the JSON wire format is
opt-in for the first deploy. Maintain existing audit-log behavior — no
changes to `AuditLogMiddleware`, `TenantOrgContextMiddleware`, or
`AuthEnforcementMiddleware` payloads.

## 2. Why this PR (not the whole Phase 2)

Phase 2 is split into three sub-PRs (per plan §6):

| Sub-PR | Scope | This PR? |
| --- | --- | :---: |
| P2.1 | Structured logging middleware + request id propagation | ✅ this PR |
| P2.2 | Job metrics endpoint + worker instrumentation | next |
| P2.3 | Phase 2 closeout MD + cross-cutting contracts | sequential after P2.1 + P2.2 |

P2.3 is **deliberately not pre-opened**: its contracts assert the
field-schema and metric counter set introduced by P2.1 + P2.2. Opening
P2.3 before P2.1 + P2.2 land would force its branch to fail until the
others merge.

## 3. Files Changed

| File | Change | Lines |
| --- | --- | ---: |
| `src/yuantus/context.py` | Add `request_id_var` ContextVar + `RequestContext.request_id` field | +3 |
| `src/yuantus/config/settings.py` | Add `LOG_FORMAT` + `REQUEST_ID_HEADER` settings | +9 |
| `src/yuantus/api/middleware/request_logging.py` | New middleware (canonical read from `request.state` after remediation) | +71 |
| `src/yuantus/api/middleware/context.py` | Snapshot `tenant_id`/`org_id` to `request.state` when setting ContextVar (remediation) | +2 |
| `src/yuantus/api/middleware/auth_enforce.py` | Snapshot `tenant_id`/`org_id`/`user_id` to `request.state` when setting ContextVar (remediation) | +3 |
| `src/yuantus/api/app.py` | Import + register middleware (outermost) | +2 |
| `src/yuantus/api/tests/test_request_logging_middleware.py` | Contract tests: 7 original + 4 chain/short-circuit (11 total) | +271 |
| `docs/DEV_AND_VERIFICATION_OBSERVABILITY_STRUCTURED_LOGGING_20260426.md` | This MD (original + §4.5 / §5 remediation) | +210 |
| `docs/DELIVERY_DOC_INDEX.md` | Index entry | +1 |

## 4. Design

### 4.1 Middleware ordering

`RequestLoggingMiddleware` is registered **last**, which makes it the
**outermost** middleware in Starlette's stack:

```
RequestLogging → AuthEnforcement → TenantOrgContext → AuditLog → CORS → endpoint
```

Reasoning:
- Inbound: `request_id_var` is set first so any inner middleware (audit,
  context, auth) can read it for correlation.
- Outbound: the final response status code observed by `RequestLogging`
  reflects all inner middleware effects (e.g., a 401 emitted by
  `AuthEnforcementMiddleware` is visible in the log line).

### 4.2 request_id resolution

1. Read `X-Request-ID` (configurable via `settings.REQUEST_ID_HEADER`).
2. Fallback: generate `uuid4().hex`.
3. Echo back into the response headers so downstream callers can
   correlate.
4. Store in the `request_id_var` ContextVar so any code path within the
   request scope can include it (logging, error reporting, audit).
5. Reset the ContextVar after the response finalises.

### 4.3 Log format

| `LOG_FORMAT` value | Wire format |
| --- | --- |
| `text` (default) | `request_id=… tenant_id=… method=GET path=/echo status_code=200 latency_ms=12` |
| `json` | `{"request_id":"…","tenant_id":null,"method":"GET",…}` |

Default is `text` to **preserve current log-line shape** for any
pre-existing log consumers. Migrating to `json` is a single env-var flip
and reversible.

### 4.4 Failure isolation

The emit step is wrapped in a bare `try/except` (matches the existing
pattern in `AuditLogMiddleware`): a logging failure must never break a
request. The ContextVar reset still happens via `finally`.

### 4.5 ContextVar lifetime — remediation (2026-04-26)

**Bug surfaced in PR #414 review** (post-rebase): the original
implementation read `tenant_id_var.get() / org_id_var.get() /
user_id_var.get()` in `RequestLoggingMiddleware.dispatch.finally`. By
that point, **inner middleware (`AuthEnforcementMiddleware`,
`TenantOrgContextMiddleware`) had already reset their tokens** in their
own `finally`. The outer `finally` runs *after* inner `finally` returns
— so the values were always `None` at log-emission time, even on
authenticated requests with tenant/org context fully resolved.

A second, related issue: the `text` format dropped `None`-valued fields
via `if fields[k] is not None`, violating plan §6's "fixed field set"
acceptance criterion (the schema must be present even when values are
`None`).

**Fix contract** (singular, no fallback):

1. Each inner middleware **snapshots** identity values to `request.state`
   *at the moment it sets the ContextVar*, not in `finally`. Snapshots
   persist for the whole request scope; `request.state` is unaffected by
   ContextVar reset.
2. `RequestLoggingMiddleware` reads canonically from `request.state` via
   `getattr(request.state, "tenant_id", None)` etc. **No ContextVar
   fallback** — request.state is the single contract; mixing both
   carries the same fragility.
3. `text` format emits **every** field key (including `None` values).

**Why test methodology let it ship**: the original `_build_minimal_app()`
helper registered only `RequestLoggingMiddleware`, so the lifetime bug
class was never exercised in tests. The new chain test
(`test_chain_log_carries_tenant_org_user_after_inner_resets_contextvars`)
registers an inner middleware that mirrors the auth/context lifetime
pattern (set + reset). Verified to **fail against the broken
implementation** before applying the fix, then pass after.

## 5. Verification

### 5.1 Boot check

```bash
PYTHONPATH=src python3 -c "from yuantus.api.app import create_app; \
  app = create_app(); print(f'app.routes: {len(app.routes)}'); \
  print(f'middleware count: {len(app.user_middleware)}')"
```

→ `app.routes: 671` (unchanged), `middleware count: 4` (was 3, +1 for the new middleware; CORS only wires when `CAD_PREVIEW_CORS_ORIGINS` is set so doesn't appear in default boot).

### 5.2 Focused contract tests

```bash
PYTHONPATH=src python3 -m pytest -q src/yuantus/api/tests/test_request_logging_middleware.py
```
→ **11 passed** in 2.19s.

Tests cover (7 original + 4 added in remediation):

Original 7:
- Middleware presence in `create_app()` user middleware stack.
- Response header carries generated request id when absent from request.
- Header pass-through when supplied via `X-Request-ID`.
- ContextVar reset after response.
- `LOG_FORMAT=text` emits k=v line.
- `LOG_FORMAT=json` emits valid JSON with required keys.
- All required fields present in JSON.

Remediation (PR #414 review follow-up):
- **Chain test (JSON)** — registers an inner middleware that mirrors auth/context lifetime (set ContextVar + snapshot to `request.state` + reset in finally); asserts the JSON log line carries `tenant_id="T1" org_id="O1" user_id="U99"`. Verified failing against the original ContextVar-read implementation; passes after the `request.state` switch.
- **Chain test (text)** — same chain, asserts the text log line contains `tenant_id=T1 org_id=O1 user_id=U99`.
- **Fixed field set on text format** — asserts every key (`request_id, tenant_id, org_id, user_id, method, path, status_code, latency_ms`) is present in text-format output even when the value is `None` (plan §6 acceptance).
- **401 short-circuit** — asserts the log line still emits with `status_code=401, tenant_id=None, org_id=None, user_id=None` when an outer middleware returns 401 before any identity context is set.

### 5.3 Broader middleware/audit/auth regression

```bash
PYTHONPATH=src python3 -m pytest -q -k "audit or context or middleware or auth"
```
→ **23 passed, 306 deselected** (was 19; +4 new logging tests).

### 5.4 API tests batch

```bash
PYTHONPATH=src python3 -m pytest -q src/yuantus/api/tests/
```
→ **29 passed, 1 skipped** (was 25; +4 new logging tests).

### 5.5 Doc-index trio

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```
→ **4 passed**.

### 5.6 Whitespace lint

```bash
git diff --check
```
→ clean.

## 6. Recipe Adherence

Per `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md` §4.3 (per-PR DOD):

- [x] One concern, bounded scope (middleware only — no audit/auth changes, no metrics).
- [x] Boot check (`create_app()`) gate post-edit.
- [x] Focused regression: 11 new tests (7 original + 4 remediation) + 23-test broader middleware/auth scan.
- [x] DEV_AND_VERIFICATION MD + index entry land in the same commit (atomicity, per `DOC_INDEX_CONTRACT_DISCIPLINE`).
- [x] Doc-index trio green.
- [x] No scope creep into P2.2 (job metrics) or P2.3 (closeout contracts).
- [x] `LOG_FORMAT=text` default preserves existing log-line shape (mitigation for risk flagged in plan §6).

## 7. Acceptance Criteria (from plan §6)

| Criterion | Status |
| --- | --- |
| Every API request log line contains `request_id, tenant_id, org_id, user_id, path, method, status_code, latency_ms` | ✅ asserted by `test_required_log_fields_are_emitted` (JSON) + `test_text_log_emits_fixed_field_set_even_when_values_are_none` (text) |
| Identity fields populated when inner middleware sets them (not blank-out by reset) | ✅ asserted by `test_chain_log_carries_tenant_org_user_*` (JSON + text) |
| Identity fields = None on auth-rejected requests | ✅ asserted by `test_log_emits_for_auth_short_circuit_with_none_identity` |
| Backwards-compatible default (text format) | ✅ default `LOG_FORMAT=text` |
| Opt-in flag `LOG_FORMAT=json` | ✅ `settings.LOG_FORMAT` |
| New contract tests guard the field set | ✅ `test_request_logging_middleware.py` (11 cases) |
| `RUNBOOK_RUNTIME.md` updated with field schema | ➡ deferred to P2.3 closeout (cross-cutting documentation) |

## 8. Out of Scope

- **Job metrics** (`/api/v1/metrics`) — P2.2.
- **Cross-cutting Phase 2 contracts** (logging fields visible to audit log, metric counter set) — P2.3.
- **`AuditLog` schema migration** to include `request_id` column — separate PR; current audit log row remains source-of-truth for persistent audit trail.
- **Sampling / rate limiting** of structured log emit — current implementation logs every request. Sampling is a Phase 6 concern (observability scaling).

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| External log consumer expects current `logging.INFO` text | Low | Low | Default `LOG_FORMAT=text` unchanged; JSON is opt-in |
| `request_id_var` collisions with concurrent requests | None | — | `ContextVar` is request-scoped via Starlette dispatch; reset in `finally` |
| Middleware registration order regression | Low | Medium | `test_request_logging_middleware_is_registered_in_app` asserts presence; order documented in §4.1 |
| Future middleware refactor drops `request_id` field | Medium | Low | Field schema asserted by `test_required_log_fields_are_emitted` |

## 10. Rollback

Pure code addition + config defaults. Revert: remove the `add_middleware`
line + the import in `app.py`. ContextVar/config setting are unused after
that.

## 11. Verification Summary

| Check | Result |
| --- | --- |
| `create_app()` boot | 671 routes, 4 middleware |
| Focused contracts (11 cases) | 11 passed |
| Chain test (broken impl pre-fix) | ✅ verified failing — confirms test would catch the original ContextVar-lifetime bug |
| Chain test (fixed impl post-fix) | ✅ passing |
| Broader middleware/audit/auth (23 cases) | 23 passed |
| API tests batch (29+1 cases) | 29 passed, 1 skipped |
| Doc-index trio | 4 passed |
| `git diff --check` | clean |
