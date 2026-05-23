# Claude Taskbook: CAD Helper Bridge S8 - CADDedupPlugin Migration And Dedup Check

Date: 2026-05-23

Type: **Doc-only taskbook.** Changes no runtime, no schema, no service, no
workflow, and no CAD plugin code. It specifies the contract a later,
separately opted-in implementation PR will deliver. Merging this taskbook does
NOT authorize that implementation.

## 1. Purpose

CAD Desktop Helper Bridge **S8** is the first slice that crosses from the helper
runtime back into the existing AutoCAD plugin package.

S8 owns:

- helper `POST /dedup/check`;
- multipart forwarding from helper to PLM `/api/dedup/check`;
- local audit extension for `/dedup/check`;
- `CADDedupPlugin.DedupApiClient.CheckDuplicateAsync(...)` migration from direct
  PLM HTTP to `Yuantus.Cad.Shared` -> helper `/dedup/check`;
- `CADDedupPlugin.MaterialSyncApiClient` migration for the S6-supported helper
  paths (`DiffPreviewAsync`, `SyncInboundAsync`, `SyncOutboundAsync`) while
  preserving the public method shapes used by `DedupPlugin`;
- `PLMMATPULL` apply-result reporting through helper `/audit/apply-result` after
  a CAD write attempt.

S8 does **not** implement S9/S10 LISP bridge code, `/shell/notify`, `/compose`,
`/validate`, `/tasks`, `/diagnostics/snapshot`, CORS, server Python routes,
database/schema migrations, new tenant-baseline data, or a CAD drawing write
adapter rewrite. Those remain separate opt-in slices.

## 2. Grounded Current Reality

Grounded against `origin/main = 431b6adf` after S7 merged.

### 2.1 R3.2 design anchors

`docs/CAD_DESKTOP_HELPER_BRIDGE_DESIGN_R3_20260519.md` defines the S8-relevant
surface:

- Lines 490-502 list helper endpoints and explicitly mark `POST /dedup/check`
  as a required helper route that forwards to `/api/dedup/check` using
  `multipart/form-data`, not JSON.
- Lines 671-695 define the SQLite `audit_events` table and include
  `/dedup/check` in the audited endpoint family.
- Lines 971-980 define the existing AutoCAD integration points:
  `MaterialSyncApiClient.cs`, `DedupApiClient.cs`, `CadMaterialFieldService.cs`,
  `MaterialSyncDiffPreviewWindow.xaml(.cs)`, `DedupPlugin.cs`, and
  `UserIdentification.cs`.
- Line 976 requires `DedupApiClient.CheckDuplicateAsync(...)` to keep its public
  API shape while migrating its internal HTTP call through
  `Yuantus.Cad.Shared` -> helper `/dedup/check`.
- Lines 975 and 979 require `MaterialSyncApiClient` and `DedupPlugin` to keep
  public API / command behavior stable while their internal transport moves
  through Shared/helper.
- Line 1064 defines S8 as `CADDedupPlugin` refactor, including
  `MaterialSyncApiClient`, `DedupApiClient`, multipart support, and
  `/audit/apply-result` reporting after `PLMMATPULL` applies CAD fields.
- Line 1071 says S8 depends on S1 + S6.

### 2.2 S1 Shared primitives inherited by S8

S1 already provides the transport primitives S8 should consume:

- `clients/cad-desktop-helper/Shared/Transport/HelperTransport.cs` exposes
  `PostJsonAsync<T>(...)`, `PostContentAsync<T>(...)`, and `GetAsync<T>(...)`.
- `PostContentAsync<T>(...)` buffers `HttpContent` so the transport can retry
  once after `AUTH_LOCAL_TOKEN_INVALID` / `AUTH_LOCAL_TOKEN_MISSING` without
  losing the content stream.
- `HelperTransport` injects `X-Yuantus-Local-Token` and
  `X-Yuantus-Protocol` on every helper request.

S8 must reuse `HelperTransport`. It must not create a second local-token reader,
second helper discovery path, or second response-envelope parser inside
`CADDedupPlugin`.

### 2.3 S6 helper business and audit substrate

S6 already merged:

- `POST /diff/preview`;
- `POST /sync/inbound`;
- `POST /sync/outbound`;
- `POST /audit/apply-result`;
- `HelperBusinessAuditService`;
- `IPlmBusinessClient` for JSON PLM forwarding;
- `SqliteAuditEventStore`;
- H1/H2 audit-write failure policy.

`docs/DEVELOPMENT_CLAUDE_TASK_CAD_HELPER_BRIDGE_S6_BUSINESS_AUDIT_ROUTES_20260522.md`
lines 270-271 explicitly says S8 must extend the audited endpoint set to include
`/dedup/check`.

S6 route count after S7 is still exactly ten:

```text
GET  /healthz
GET  /version
POST /session/login
POST /session/logout
GET  /session/status
POST /cad/current-drawing
POST /diff/preview
POST /sync/inbound
POST /sync/outbound
POST /audit/apply-result
```

S8 is the first route-count bump after S6. After S8, the helper production route
count must be exactly eleven.

### 2.4 Existing CADDedupPlugin HTTP clients

`clients/autocad-material-sync/CADDedupPlugin/MaterialSyncApiClient.cs` currently:

- constructs a direct `HttpClient` pointed at `DedupConfig.ServerUrl`;
- injects direct PLM bearer and tenant/org headers from `DedupConfig`;
- exposes public methods `GetProfilesAsync`, `GetProfileAsync`, `ComposeAsync`,
  `ValidateAsync`, `SyncInboundAsync`, `SyncOutboundAsync`, and
  `DiffPreviewAsync`;
- sends direct JSON calls to `/api/v1/plugins/cad-material-sync/...`.

`clients/autocad-material-sync/CADDedupPlugin/DedupApiClient.cs` currently:

- constructs a direct `HttpClient` pointed at `DedupConfig.ServerUrl`;
- injects direct PLM bearer from `DedupConfig.ApiKey`;
- `CheckDuplicateAsync(string filePath)` opens the DWG using
  `FileShare.ReadWrite`;
- sends multipart parts `file`, `threshold`, `auto_index`, and `file_path` to
  `/api/dedup/check`;
- updates `_lastResult` and `UsageStatistics` after a successful response.

### 2.5 Existing AutoCAD command coupling

`clients/autocad-material-sync/CADDedupPlugin/DedupPlugin.cs` currently:

- calls `DedupApiClient.CheckDuplicateAsync(...)` from the duplicate-check flows;
- calls `MaterialSyncApiClient.SyncInboundAsync(...)` from `PLMMATPUSH`;
- calls `MaterialSyncApiClient.DiffPreviewAsync(...)` from `PLMMATPULL`;
- applies confirmed `write_cad_fields` through
  `CadMaterialFieldService.ApplyFields(...)`.

`MaterialDiffPreviewResponse` currently has no `PullId` property. The S6 helper
`/diff/preview` response shape is:

```json
{
  "pull_id": "PULL-...",
  "server_response": { "...": "..." }
}
```

Therefore S8 cannot simply deserialize the helper response directly into the
existing `MaterialDiffPreviewResponse`. It must unwrap `server_response` and
carry `pull_id` through an added, public-shape-preserving field/property for
`/audit/apply-result`.

### 2.6 Current verification reality

The existing AutoCAD plugin project
`clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj` requires real
AutoCAD managed assemblies (`accoremgd.dll`, `acdbmgd.dll`, `acmgd.dll`,
`AcWindows.dll`, `AdWindows.dll`). The normal GitHub Windows runner does not have
AutoCAD installed.

Existing non-AutoCAD checks include:

- `clients/autocad-material-sync/verify_material_sync_static.py`;
- fixture/e2e scripts under `clients/autocad-material-sync/`;
- `.github/workflows/cad-helper-shared-dotnet.yml`, which currently covers
  Shared, Detector, and Helper projects, but not the AutoCAD plugin package.

S8 implementation must add verification that is honest about this split:

- SDK-free CI for helper/shared/plugin-client contracts;
- manual Windows + AutoCAD evidence deferred to operational signoff unless the
  owner explicitly provides a real Windows AutoCAD environment for the PR.

## 3. S8 Decisions And Boundaries

### 3.A Route surface

S8 implementation adds exactly one production helper route:

```text
POST /dedup/check
```

After S8, production helper route declarations must be exactly eleven:

```text
GET  /healthz
GET  /version
POST /session/login
POST /session/logout
GET  /session/status
POST /cad/current-drawing
POST /diff/preview
POST /sync/inbound
POST /sync/outbound
POST /audit/apply-result
POST /dedup/check
```

No S9/S10/S11 or R3+ routes may appear:

- `/shell/notify`;
- `/compose`;
- `/validate`;
- `/tasks`;
- `/diagnostics/snapshot`;
- HTTP reset-token routes;
- LISP bridge endpoints.

### 3.B Security and session policy

`/dedup/check` is a normal helper business route:

- S4 local-token auth required;
- S4 protocol header required;
- S4 origin allowlist required;
- no CORS;
- no browser `Authorization` header forwarding;
- S5 `server_url` and PLM bearer required before forwarding to PLM;
- PLM bearer must be used only by helper internals for the outbound PLM call.

Missing session state returns the same helper-envelope family as S6:

- missing/invalid `server_url` / tenant config -> `AUTH_TENANT_MISSING` or
  `PLM_VALIDATION_FAILED` as appropriate;
- missing PLM bearer -> `AUTH_PLM_NOT_LOGGED_IN`;
- no PLM call is made in either case.

### 3.C RATIFY: MaterialSyncApiClient migration scope

There is a real scope tension in the R3.2 design:

- R3.2 line 1064 says S8 migrates `MaterialSyncApiClient` HTTP calls.
- The existing `MaterialSyncApiClient` also contains `GetProfilesAsync`,
  `GetProfileAsync`, `ComposeAsync`, and `ValidateAsync`.
- R3.2 lines 504-505 explicitly defer `/compose` and `/validate` to R3+.
- The helper has no `profiles` route today.

This taskbook recommends and **requires reviewer ratification of Option A**:

**Option A - S8-R1 migrates only helper-supported MaterialSync methods plus
DedupApiClient.**

S8-R1 migrates:

- `MaterialSyncApiClient.DiffPreviewAsync(...)` -> helper `/diff/preview`;
- `MaterialSyncApiClient.SyncInboundAsync(...)` -> helper `/sync/inbound`;
- `MaterialSyncApiClient.SyncOutboundAsync(...)` -> helper `/sync/outbound`;
- `DedupApiClient.CheckDuplicateAsync(...)` -> helper `/dedup/check`.

S8-R1 does **not** migrate:

- `GetProfilesAsync`;
- `GetProfileAsync`;
- `ComposeAsync`;
- `ValidateAsync`.

Those remain direct PLM calls until a later, separately opted-in profile/compose
route slice exists. The S8 implementation and PR body must not claim that helper
is the unique PLM exit for every AutoCAD plugin command after S8. The honest
claim is narrower: helper becomes the PLM exit for dedup check, PLMMATPUSH,
PLMMATPULL diff preview, and PLMMATPULL apply-result reporting.

Rejected for S8-R1 unless reviewer rewrites this taskbook:

- **Option B**: add helper profiles/compose/validate routes in S8 and migrate all
  `MaterialSyncApiClient` methods. This widens S8 beyond `/dedup/check` and the
  already-merged S6 route surface.
- **Option C**: delete or disable PLMMATCOMPOSE/profile commands. This is a
  behavior regression.

### 3.D `/dedup/check` multipart contract

`POST /dedup/check` is multipart, not JSON.

Incoming helper request expectations:

- `Content-Type` must be `multipart/form-data`.
- Required file part: `file`.
- Forwarded text parts from the existing plugin contract:
  - `threshold`;
  - `auto_index`;
  - `file_path`.

The helper forwards to:

```text
POST <server_url>/api/dedup/check
```

Outbound PLM request requirements:

- uses S5 PLM bearer as `Authorization: Bearer <token>`;
- forwards a multipart/form-data body, not JSON;
- preserves the file part name as `file`;
- preserves the filename supplied by the AutoCAD client;
- preserves `threshold`, `auto_index`, and `file_path` text fields;
- does not add local helper token, origin process data, or browser headers to the
  PLM-bound request body.

Validation policy:

- non-multipart request -> helper envelope `ok=false` with
  `HELPER_INPUT_VALIDATION_FAILED`;
- missing `file` part -> `HELPER_INPUT_VALIDATION_FAILED`;
- malformed multipart parse -> `HELPER_INPUT_VALIDATION_FAILED`;
- helper validation failures do not call PLM and do not create an audit row.

### 3.E `/dedup/check` audit policy

S8 extends the S6 audited endpoint set with `/dedup/check`.

Audit row for `/dedup/check`:

- `endpoint = "/dedup/check"`;
- `drawing_path = file_path` when present;
- `profile_id = null`;
- `item_id = null`;
- `pull_id = null`;
- `cad_system = "autocad"` if the request or S8 helper code can infer it
  without parsing CAD file content; otherwise `null`;
- `outcome = "ok"` when the helper-visible PLM result is success;
- `outcome = "failed"` when the helper-visible PLM result is an error;
- `error_code` is the helper/PLM error code on failure;
- `duration_ms` measures helper receipt -> PLM result -> audit write attempt;
- `trace_id` uses the same `Guid.NewGuid().ToString("N")` format as S6/S7.

The audit row is written after the PLM response is received and helper-visible
outcome is known, not before.

Failure policy extends S6 H2:

- PLM success + audit write failure -> preserve PLM success response and emit one
  sanitized stderr line:

```text
[AUDIT_WRITE_FAILED] endpoint=/dedup/check trace_id=<id> reason=<short>
```

- bearer token, file path, request bodies, and file bytes must not appear in that
  line;
- PLM failure remains visible to the caller even if the audit write also fails;
- `/audit/apply-result` remains the only H1 fail-closed audit route.

### 3.F Helper implementation shape

Implementation may extend `HelperBusinessAuditService` or introduce an adjacent
service seam, but must preserve S6 behavior.

Recommended shape:

- add `IPlmMultipartClient` / `HttpPlmMultipartClient` rather than overloading the
  JSON-only `IPlmBusinessClient.PostAsync(...)` with multipart semantics;
- reuse `TryReadSession(...)` behavior for S5 config + bearer;
- reuse S6 `WriteAuditAfterBusiness(...)` semantics where practical;
- ensure `/dedup/check` tests can fake multipart forwarding without a real PLM
  server;
- do not parse or log DWG file bytes;
- do not write any CAD file from helper.

### 3.G CADDedupPlugin transport migration

S8 implementation must add a `ProjectReference` from
`CADDedupPlugin.csproj` to `clients/cad-desktop-helper/Shared/Yuantus.Cad.Shared.csproj`.

The AutoCAD plugin must consume the Shared **net46** target. It must preserve:

- AutoCAD 2018 default `TargetFrameworkVersion = v4.6`;
- AutoCAD 2024 explicit `v4.8` path;
- `PlatformTarget = x64`;
- existing `PackageContents.*.xml`;
- existing public command names:
  - `DEDUPCHECK`;
  - `DEDUPVIEW`;
  - `PLMMATPROFILES`;
  - `PLMMATCOMPOSE`;
  - `PLMMATPUSH`;
  - `PLMMATPULL`.

`DedupConfig.ServerUrl`, `ApiKey`, `TenantId`, and `OrgId` are not used for the
migrated helper-bound calls. Session state and PLM bearer are owned by helper
S5. Existing config fields may remain for legacy commands not migrated in S8-R1
per §3.C.

### 3.H MaterialSyncApiClient helper adaptation

For the three S6-supported methods, `MaterialSyncApiClient` must keep its public
method signatures and return types stable:

- `DiffPreviewAsync(...)`;
- `SyncInboundAsync(...)`;
- `SyncOutboundAsync(...)`.

The internal transport changes to `HelperTransport`.

`DiffPreviewAsync(...)` must adapt helper response shape:

1. call helper `/diff/preview`;
2. read helper data `{ pull_id, server_response }`;
3. deserialize `server_response` into the existing `MaterialDiffPreviewResponse`
   shape;
4. carry the helper `pull_id` through a new `PullId` property or equivalent
   internal-accessible field so `DedupPlugin.PLMMATPULL` can report
   `/audit/apply-result`;
5. keep existing UI consumption (`WriteCadFields`, `Diffs`,
   `RequiresConfirmation`, etc.) unchanged.

`SyncInboundAsync(...)` and `SyncOutboundAsync(...)` must return the same
`MaterialSyncResponse` shape callers receive today.

### 3.I DedupApiClient helper adaptation

`DedupApiClient.CheckDuplicateAsync(string filePath)` must keep its public method
signature and return type stable.

Required preserved behavior:

- rejects missing files before helper call with the existing `FileNotFoundException`
  behavior;
- opens the DWG with `FileShare.ReadWrite`;
- sends multipart parts `file`, `threshold`, `auto_index`, and `file_path`;
- stores `_lastResult`;
- updates `UsageStatistics` after a successful response exactly as today.

Changed behavior:

- posts to helper `/dedup/check` via `HelperTransport.PostContentAsync<DedupResult>(...)`;
- no direct `HttpClient.PostAsync("/api/dedup/check", ...)` call remains in
  `DedupApiClient`;
- no direct PLM bearer header is set for migrated dedup calls.

`TestConnectionAsync()` is outside S8-R1 unless reviewer ratifies otherwise. It
may remain direct to PLM because helper has no health-forwarding route to PLM;
implementation must document this as a remaining legacy direct call rather than
claiming complete PLM-exit closure.

### 3.J PLMMATPULL apply-result reporting

After `PLMMATPULL` receives a successful helper-backed diff preview and the user
confirms a CAD write attempt, `DedupPlugin` must call helper
`/audit/apply-result` with:

- `pull_id` from the helper diff preview;
- `outcome = "ok"` if `CadMaterialFieldService.ApplyFields(...)` returns without
  throwing;
- `outcome = "failed"` if `ApplyFields(...)` throws after the preview succeeded;
- `applied_fields` equal to the attempted write field dictionary when the write
  returns without throwing;
- `failed_fields` populated with the attempted field dictionary or an error
  marker when `ApplyFields(...)` throws;
- `drawing.filename` and `drawing.filepath` derived from the current AutoCAD
  document path;
- `cad_system = "autocad"`;
- `duration_ms` measured around the CAD write attempt.

If the user cancels the diff preview before any write attempt, S8-R1 does not
call `/audit/apply-result`. The existing `/diff/preview` audit row remains the
record that the preview occurred.

If helper `/audit/apply-result` fails after a successful CAD write, the plugin
must not roll back CAD writes. It should write a clear AutoCAD command-line
warning with the helper error code and continue. This mirrors the reality that
DWG writes are already committed inside the AutoCAD process and the helper audit
write is not transactional with them.

### 3.K Error code policy

S8 reuses existing error codes where possible:

- `HELPER_INPUT_VALIDATION_FAILED` for helper multipart validation failures;
- `AUTH_TENANT_MISSING`;
- `AUTH_PLM_NOT_LOGGED_IN`;
- `PLM_VALIDATION_FAILED`;
- `AUDIT_WRITE_FAILED`.

No new error code is required unless implementation discovers a concrete
non-overlapping failure class. Any new code must be added to
`Yuantus.Cad.Shared.Transport.ErrorCodes` and pinned by tests.

HTTP status policy stays the S6 ratified rule:

- business/helper validation errors return HTTP 200 + helper envelope `ok=false`;
- S4 auth/origin/protocol errors remain HTTP-layer 4xx/426.

### 3.L Verification and workflow policy

S8 must extend the dedicated Windows .NET workflow so it catches S8 changes that
do not require AutoCAD assemblies.

Required CI posture:

- `.github/workflows/cad-helper-shared-dotnet.yml` path filters include
  `clients/autocad-material-sync/**`;
- workflow continues to build/test Shared, Detector, and Helper;
- workflow runs `python clients/autocad-material-sync/verify_material_sync_static.py`;
- implementation adds SDK-free contract coverage for migrated client behavior.

Recommended SDK-free test shape:

- create an AutoCAD-SDK-free test project that links or compiles only the
  transport/client source files required to test `MaterialSyncApiClient` and
  `DedupApiClient`;
- do not reference AutoCAD managed assemblies in that test project;
- do not require real AutoCAD installation on GitHub runners.

The real `CADDedupPlugin.csproj` build/load still requires Windows + AutoCAD
2018/2024 and remains manual operational evidence.

### 3.M Manual Windows AutoCAD evidence posture

S8 implementation should continue the risk-downgrade posture used by S7 unless
the owner provides a real Windows + AutoCAD environment before merge.

Required documentation if manual evidence is unavailable:

- DEV/Verification MD must explicitly say Windows AutoCAD build/load/smoke was
  not run locally;
- PR body must explicitly list deferred operational evidence;
- merge must not be represented as Windows AutoCAD validation.

Deferred evidence for S8:

- Windows + AutoCAD 2018 build of `CADDedupPlugin.csproj`;
- AutoCAD loads `CADDedup.bundle`;
- `DEDUPCHECK` routes through helper `/dedup/check` and records local audit;
- `PLMMATPUSH` routes through helper `/sync/inbound`;
- `PLMMATPULL` routes through helper `/diff/preview`, writes CAD fields, and
  posts `/audit/apply-result`;
- helper audit DB contains `/dedup/check` and `/audit/apply-result` rows for the
  smoke run.

This is not a substitute for evidence. It is a conscious implementation-merge
risk posture so the repo can keep moving without pretending this workstation can
prove AutoCAD runtime behavior.

## 4. R1 Target Output

Implementation PR should contain:

- helper runtime support for `POST /dedup/check`;
- multipart PLM forwarding seam;
- `/dedup/check` audit integration;
- `CADDedupPlugin.csproj` Shared `ProjectReference`;
- `MaterialSyncApiClient` helper-backed implementations for
  `DiffPreviewAsync`, `SyncInboundAsync`, and `SyncOutboundAsync`;
- `DedupApiClient.CheckDuplicateAsync` helper-backed multipart upload;
- `PLMMATPULL` apply-result reporting after CAD write attempts;
- narrow guard-test updates for route count 10 -> 11 and `/dedup/check`
  allowance;
- SDK-free test coverage for client migration behavior;
- workflow update for AutoCAD material sync static checks and any SDK-free client
  tests;
- `docs/DEV_AND_VERIFICATION_CAD_HELPER_BRIDGE_S8_DEDUP_PLUGIN_MIGRATION_R1_20260523.md`;
- one `docs/DELIVERY_DOC_INDEX.md` line.

## 5. Mandatory Tests

S8 implementation must add these exactly named tests, either in one test file or
split by project where appropriate:

1. `test_s8_adds_exactly_dedup_check_route_and_preserves_prior_routes`
2. `test_dedup_check_route_is_protected_by_s4_security_gate`
3. `test_dedup_check_requires_logged_in_session_before_plm_forwarding`
4. `test_dedup_check_rejects_non_multipart_or_missing_file_without_plm_call`
5. `test_dedup_check_forwards_multipart_file_threshold_auto_index_and_file_path`
6. `test_dedup_check_preserves_plm_errors_without_collapsing_to_success`
7. `test_dedup_check_writes_audit_row_after_plm_result`
8. `test_dedup_check_audit_failure_after_plm_success_warns_but_returns_success`
9. `test_s8_extends_audited_endpoint_set_to_include_dedup_check_only`
10. `test_material_sync_client_migrates_s6_supported_methods_to_helper_transport`
11. `test_material_sync_client_unwraps_helper_diff_preview_pull_id_and_server_response`
12. `test_material_sync_auxiliary_methods_remain_explicit_legacy_direct_calls`
13. `test_dedup_api_client_posts_multipart_to_helper_not_direct_plm`
14. `test_dedup_api_client_preserves_file_share_readwrite_and_usage_statistics`
15. `test_caddedup_plugin_references_shared_net46_without_changing_autocad_targets`
16. `test_plmmatpull_reports_audit_apply_result_after_successful_write_attempt`
17. `test_plmmatpull_write_failure_reports_failed_apply_result_without_swallowing_cad_error`
18. `test_plmmatpull_cancel_does_not_report_apply_result`
19. `test_s8_keeps_no_lisp_shell_compose_validate_tasks_or_cors_scope`
20. `test_s8_workflow_runs_helper_tests_and_autocad_static_contracts`

Source/drift guards:

- exactly eleven helper production route declarations after S8;
- `MapPost("/dedup/check"` present exactly once;
- no `/shell/notify`, `/compose`, `/validate`, `/tasks`,
  `/diagnostics/snapshot`, or HTTP reset route;
- no `UseCors`;
- no browser `Authorization` header forwarding;
- no token string in audit rows, helper responses, AutoCAD command output, or
  stderr;
- no direct `/api/dedup/check` call remains in `DedupApiClient`;
- no direct PLM calls remain in `MaterialSyncApiClient.DiffPreviewAsync`,
  `SyncInboundAsync`, or `SyncOutboundAsync`;
- `MaterialSyncApiClient.GetProfilesAsync`, `GetProfileAsync`, `ComposeAsync`,
  `ValidateAsync`, and `DedupApiClient.TestConnectionAsync` are either still
  explicitly direct legacy calls per §3.C/§3.I or moved only if the reviewer
  rewrites this taskbook;
- AutoCAD project targeting remains v4.6 for 2018 and v4.8 for the 2024 path.

## 6. Verification Plan

Local doc-contract checks:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py \
  src/yuantus/meta_engine/tests/test_tier_b_3_breakage_design_loopback_portfolio_contract.py
```

Static client checks expected in implementation:

```bash
python3 clients/autocad-material-sync/verify_material_sync_static.py
xmllint --noout \
  clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj \
  clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml \
  clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml \
  clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml
```

.NET verification expected from GitHub Windows workflow:

```bash
dotnet build clients/cad-desktop-helper/Shared/Yuantus.Cad.Shared.csproj --configuration Release --no-restore
dotnet test  clients/cad-desktop-helper/Shared.Tests/Yuantus.Cad.Shared.Tests.csproj --configuration Release --no-restore
dotnet build clients/cad-desktop-helper/Helper/Yuantus.Cad.Helper.csproj --configuration Release --no-restore
dotnet test  clients/cad-desktop-helper/Helper.Tests/Yuantus.Cad.Helper.Tests.csproj --configuration Release --no-restore
```

If S8 adds an SDK-free AutoCAD client test project, the workflow must also run
that project's restore/build/test steps.

This workstation does not have a local .NET SDK or AutoCAD runtime. Do not claim
local `.NET` or AutoCAD test success unless those commands are actually run in an
environment that supports them.

## 7. DEV/Verification MD Requirements

The S8 implementation DEV/Verification MD must record:

- final route count;
- exact helper endpoint added;
- exact migrated plugin methods;
- exact legacy direct-call methods still left by §3.C / §3.I;
- audit behavior for `/dedup/check`;
- `PLMMATPULL` apply-result behavior;
- workflow changes;
- local verification commands and outputs;
- GitHub Windows workflow run URL / run id;
- manual Windows AutoCAD evidence status, including any deferred operational
  signoff items from §3.M.

## 8. Explicit Non-Goals

- No S9/S10 LISP bridge.
- No `/shell/notify`.
- No `/compose` or `/validate` helper route in S8-R1.
- No helper profile routes in S8-R1 unless reviewer rejects §3.C Option A.
- No CORS.
- No browser `Authorization` forwarding.
- No Python FastAPI or plugin server changes.
- No database/schema/migration/tenant-baseline changes.
- No rewrite of `CadMaterialFieldService` or DWG write algorithms.
- No AutoCAD package metadata widening beyond the Shared reference needed for S8.
- No claim that helper is the unique PLM exit for every AutoCAD plugin command
  until the legacy direct-call methods in §3.C / §3.I are handled by a later
  route slice.

## 9. Recommended Branch

Implementation branch after this taskbook merges and receives separate opt-in:

```text
feat/cad-helper-bridge-s8-dedup-plugin-migration-r1-20260523
```

## 10. Reviewer Focus

Review should focus on:

1. Ratify or reject §3.C Option A. This is the central scope decision.
2. Confirm `/dedup/check` multipart validation and forwarding rules in §3.D.
3. Confirm `/dedup/check` uses S6 H2 audit failure behavior in §3.E.
4. Confirm `PLMMATPULL` cancel / success / failure audit semantics in §3.J.
5. Confirm `TestConnectionAsync` remains a documented legacy direct call in
   §3.I.
6. Confirm the workflow and SDK-free test posture in §3.L is sufficient without
   pretending GitHub can build the AutoCAD plugin DLL.
7. Confirm the S8 manual Windows AutoCAD evidence is deferred operational
   signoff unless the owner provides a real Windows AutoCAD environment.
