# Claude Taskbook: CAD Helper Bridge S3 - Helper Startup

Date: 2026-05-21

Type: **Doc-only taskbook.** Changes no runtime, no schema, no service, no
workflow, and no CAD plugin code. It specifies the contract a later,
separately opted-in implementation PR will deliver. Merging this taskbook does
NOT authorize that implementation.

## 1. Purpose

CAD Desktop Helper Bridge **S3** (per #614 `fff93a2` section 10) introduces the
first real `yuantus-cad-helper.exe` service slice:

- `clients/cad-desktop-helper/Helper/` .NET 6 Windows helper executable;
- Kestrel loopback startup on `127.0.0.1` only;
- deterministic port allocation across `7959..7999`;
- `helper-session-{sessionId}.json` lifecycle;
- `Local\YuantusCadHelper-{installId}` mutex ownership and singleton recovery;
- bare `/healthz` endpoint for S1 `HelperProbe` and `HelperLocator`;
- local-token bootstrap through the S1 `LocalTokenStore` primitive;
- default 30-minute idle shutdown;
- Windows .NET workflow coverage for Helper and Helper.Tests.

S3 is still startup infrastructure only. It does **not** implement local-token
auth, origin allowlisting, session login, CAD context routes, business
endpoints, reset-token CLI, SQLite audit, plugin migration, or CAD writes. Those
remain S4-S11, each requiring its own taskbook and implementation opt-in.

Prerequisites already merged:

- #614 `fff93a2`: CAD helper bridge R3.2 design.
- #616 `bd61af2`: S1 Shared taskbook.
- #617 `2740865`: S1 Shared implementation.
- #618 `db1d3de`: S2 Detector implementation and Windows .NET CI wiring.

## 2. Current Reality (grounded by direct reads)

Grounded against `origin/main = db1d3de`.

### 2.1 R3.2 design source

`docs/CAD_DESKTOP_HELPER_BRIDGE_DESIGN_R3_20260519.md` defines the S3 surface:

- Section 5.1: `yuantus-cad-helper.exe` is a single-file .NET 6 executable
  deployed under `%APPDATA%\YuantusPLM\helper\yuantus-cad-helper.exe`.
- Section 5.1: helper is **not** a startup item. CAD-side callers spawn it when
  needed, then poll `/healthz` for up to five seconds.
- Section 5.1: helper owns a named mutex
  `Local\YuantusCadHelper-{installId}`. The `Local\` namespace is session
  scoped.
- Section 5.1: idle timeout defaults to 30 minutes and may be overridden by
  `config.json`.
- Section 5.1: the R3.2 singleton recovery flow distinguishes a healthy
  existing helper, stale session files, PID reuse via image-path mismatch, and
  an unhealthy still-running helper.
- Section 5.2: helper-session schema includes
  `schema_version`, `session_id`, `port`, `pid`, `image_path`, `started_at`,
  `protocol_version`, `helper_version`, and `endpoints_base`.
- Section 5.3.1: helper is the local-token producer. It writes a DPAPI-protected
  32-byte random token before `/healthz` can return healthy.
- Section 5.3.2: `--reset-local-token` exists in the R3 design but is a separate
  interactive CLI slice. S3 does not implement it.
- Section 10: S3 is specifically "Kestrel loopback + port allocation +
  helper-session lifecycle + consume Shared.InstallId.GetOrCreate to assemble
  the mutex + singleton recovery full algorithm + bootstrap token generation".

### 2.2 S1 Shared implementation already available

`clients/cad-desktop-helper/Shared/` now provides the primitives S3 must consume:

- `Identity/Paths.cs`
  - `ProtocolVersion = "1.0"`;
  - `HelperExeName = "yuantus-cad-helper.exe"`;
  - `RootDirectory = %APPDATA%\YuantusPLM`;
  - `HelperExePath = %APPDATA%\YuantusPLM\helper\yuantus-cad-helper.exe`;
  - `HelperSessionFilePath = helper-session-{SessionContext.CurrentSessionId}.json`.
- `Identity/InstallId.cs`
  - atomic `install-id.json` creation using `FileMode.CreateNew`;
  - winner writes; losers re-read;
  - corrupt or unavailable files raise `HELPER_INSTALL_ID_UNAVAILABLE`.
- `Discovery/HelperSessionFile.cs`
  - reads the exact session schema from R3.2;
  - returns `null` for missing, empty, IO-incomplete, unauthorized, or malformed
    files;
  - keeps `FileShare.ReadWrite | FileShare.Delete` so helper-side atomic writes
    and cleanup can coexist with polling.
- `Discovery/HelperProbe.cs`
  - performs bare GET `/healthz`;
  - injects no `X-Yuantus-Local-Token`;
  - requires status 200 and a JSON body with either `{ "ok": true }` or
    `{ "status": "ok" }`;
  - rejects a plain 200 body.
- `Discovery/HelperLocator.cs`
  - reads session file, probes health, otherwise spawns helper;
  - waits up to five seconds with 100 ms polling.
- `Security/LocalTokenStore.cs`
  - writes and reads the DPAPI-protected local helper token;
  - wraps write failure as `HELPER_LOCAL_TOKEN_BOOTSTRAP_FAILED`.
- `Transport/ErrorCodes.cs`
  - already declares `HELPER_SINGLETON_LOST`, `HELPER_UNHEALTHY`,
    `HELPER_LOCAL_TOKEN_BOOTSTRAP_FAILED`, `HELPER_PORT_BUSY`, and related
    codes.

### 2.3 S2 Detector implementation is separate and read-only

S2 added:

- `clients/cad-desktop-helper/Detector/Yuantus.Cad.Detector.csproj`;
- `clients/cad-desktop-helper/Detector.Tests/Yuantus.Cad.Detector.Tests.csproj`;
- read-only registry and filesystem CAD detection;
- no Kestrel, no endpoint, no mutex, no session lifecycle, no local-token
  bootstrap.

S3 must not modify Detector behavior.

### 2.4 Existing Windows .NET workflow

`.github/workflows/cad-helper-shared-dotnet.yml` currently triggers on:

- Shared and Shared.Tests paths;
- Detector and Detector.Tests paths;
- the workflow file itself.

It restores, builds, and tests Shared and Detector on `windows-latest`.

S3 implementation must extend this workflow with Helper and Helper.Tests paths
plus restore/build/test steps. This is required because local macOS verification
does not provide the authoritative Windows .NET SDK signal.

## 3. Ratified S3 Boundaries

### 3.A Helper project shape

S3 implementation owns exactly these new project roots:

```text
clients/cad-desktop-helper/Helper/
clients/cad-desktop-helper/Helper.Tests/
```

Expected project contracts:

- Project SDK: `Microsoft.NET.Sdk.Web`, because S3 owns the Kestrel host.
- Helper executable target: `net6.0-windows`.
- Assembly name: `yuantus-cad-helper`.
- Root namespace: `Yuantus.Cad.Helper`.
- Reference `..\Shared\Yuantus.Cad.Shared.csproj`.
- Use ASP.NET Core/Kestrel only inside Helper.
- Tests target `net6.0-windows`, using the same xUnit family as S1/S2 tests.
- `EnableWindowsTargeting` escape hatch is allowed for non-Windows build agents,
  consistent with S1/S2.
- Runtime identifiers should include `win-x64;win-x86` so the helper remains
  publishable for R3 desktop deployment, but S3 R1 CI acceptance is build/test,
  not an installer or packaging artifact.

No solution file is required in S3. If a solution is added later, that belongs
to S11 integration unless a separate taskbook narrows the scope.

### 3.B Minimal endpoint carve-out: `/healthz` belongs to S3

S3 owns exactly one HTTP endpoint:

```text
GET /healthz
```

Contract:

- No local-token header required.
- No origin allowlist required.
- No tenant, PLM token, session, CAD context, or user identity required.
- Response is JSON accepted by S1 `HelperProbe`, specifically `{ "ok": true }`
  is sufficient and preferred.
- It must not return healthy until:
  - mutex ownership is established;
  - local-token bootstrap has completed;
  - a loopback port is bound;
  - the session file has been written with the current process metadata.

This is an intentional refinement of #614: S5 still owns `/version`,
`/session/*`, `/cad/current-drawing`, and all richer route semantics. S3 owns
only the minimal `/healthz` needed for startup discovery.

### 3.C Loopback binding and port allocation

S3 binds only to:

```text
127.0.0.1
```

Port allocation:

- Try ports linearly from `7959` through `7999`, inclusive.
- First bind success wins.
- Never bind `0.0.0.0`, `localhost`, `::1`, or a random OS-assigned port.
- If the whole range is unavailable, fail with `HELPER_PORT_BUSY`.

IPv6 support is out of S3. The R3.2 contract and S1 `HelperProbe` both use
`127.0.0.1`.

### 3.D Mutex ownership and singleton recovery

S3 consumes `InstallId.GetOrCreate()` and uses the exact mutex name:

```text
Local\YuantusCadHelper-{installId}
```

Ratified behavior:

- A process that acquires the mutex becomes the active helper for the current
  Windows session.
- A second process that finds a healthy existing helper exits `0` without
  starting another server.
- A second process that cannot read the session file waits 500 ms and retries
  the mutex flow up to three total attempts.
- If all missing-session attempts fail, exit with error code
  `HELPER_SINGLETON_LOST`.
- If a session file exists but `/healthz` is unhealthy, the process inspects
  the recorded PID and image path:
  - process missing: stale, delete session file, retry;
  - process exists but image path differs from `image_path`: stale/PID reuse,
    delete session file, retry;
  - process exists and image path equals `image_path`: return
    `HELPER_UNHEALTHY` and do **not** delete the session file.

Process exit model:

- healthy existing helper: process exit code `0`;
- startup failure: process exit code `1`;
- stderr carries the Shared-style error code string. The string code is the
  stable contract; numeric exit code is intentionally coarse.

### 3.E Session file lifecycle

S3 writes the current session discovery file:

```text
%APPDATA%\YuantusPLM\helper-session-{sessionId}.json
```

Schema must exactly cover the S1 `HelperSessionFile` fields:

```json
{
  "schema_version": "1.0",
  "session_id": 2,
  "port": 7959,
  "pid": 12345,
  "image_path": "C:\\Users\\frank\\AppData\\Roaming\\YuantusPLM\\helper\\yuantus-cad-helper.exe",
  "started_at": "2026-05-21T10:00:00-07:00",
  "protocol_version": "1.0",
  "helper_version": "0.1.0",
  "endpoints_base": "http://127.0.0.1:7959"
}
```

File write policy:

- Ensure `%APPDATA%\YuantusPLM` exists.
- Write a complete JSON document through a temp file under the same directory.
- Atomically publish the final session file by replace/move.
- Do not leave an empty or partial final session file on successful startup.

Cleanup policy:

- On normal shutdown, cancellation, or idle timeout, delete only the current
  session file.
- Cleanup is best effort; cleanup failure should not hang process exit.
- Crash leftovers are handled by the next startup's singleton recovery flow.

### 3.F Local-token bootstrap

S3 is the first slice that decides **when** S1 `LocalTokenStore.WriteLocalToken`
is called.

Ratified behavior:

- At startup, read the existing local token through `LocalTokenStore.ReadLocalToken()`.
- If present and non-empty, reuse it.
- If missing or empty, generate a new token:
  - `RandomNumberGenerator.GetBytes(32)`;
  - lowercase hex encoding;
  - 64 hex characters;
  - write through `LocalTokenStore.WriteLocalToken(...)`.
- Bootstrap must finish before `/healthz` can return healthy.
- If token write fails, startup fails with
  `HELPER_LOCAL_TOKEN_BOOTSTRAP_FAILED`, no final session file is published,
  and no healthy `/healthz` is exposed.

S3 does **not** implement token reset. `--reset-local-token` is still S7.

### 3.G Idle timeout

S3 implements idle shutdown:

- default timeout: 30 minutes;
- any accepted HTTP request, including `/healthz`, refreshes last-activity time;
- once idle timeout elapses, helper exits gracefully and deletes the current
  session file.

Config override:

- Optional read from `%APPDATA%\YuantusPLM\config.json`;
- field: `idle_timeout_minutes`;
- valid values: integer `1..1440`;
- missing file, missing field, malformed JSON, non-integer value, or out-of-range
  value all fall back to 30 minutes;
- config read failure must not prevent startup.

This keeps S3 faithful to #614 while avoiding a broader configuration surface.
S5 remains responsible for session configuration and PLM identity.

### 3.H Workflow coverage

S3 implementation must update `.github/workflows/cad-helper-shared-dotnet.yml`:

- add pull_request and push path filters for:
  - `clients/cad-desktop-helper/Helper/**`;
  - `clients/cad-desktop-helper/Helper.Tests/**`;
- restore Helper.Tests;
- build Helper;
- test Helper.Tests;
- keep existing Shared and Detector steps.

The PR must cite the dedicated workflow run for the implementation SHA. The
generic `contracts` check is not sufficient for .NET build/test coverage.

### 3.I No scope leak into S4-S11

S3 must not introduce:

- local-token validation middleware;
- `X-Yuantus-Local-Token` enforcement;
- origin PID/path allowlisting;
- PLM bearer-token storage;
- `/version`;
- `/session/login`, `/session/logout`, `/session/status`;
- `/cad/current-drawing`;
- `/diff/preview`, `/sync/inbound`, `/sync/outbound`;
- `/audit/apply-result`;
- SQLite audit database;
- `--reset-local-token`;
- CADDedupPlugin migration;
- LISP bridge;
- ZWCAD/GstarCAD shell;
- new server-side Python route, schema, migration, or tenant baseline.

## 4. R1 Target Output

The later S3 implementation PR should contain:

- `clients/cad-desktop-helper/Helper/Yuantus.Cad.Helper.csproj`;
- `clients/cad-desktop-helper/Helper.Tests/Yuantus.Cad.Helper.Tests.csproj`;
- helper startup/runtime code under `clients/cad-desktop-helper/Helper/`;
- focused xUnit tests under `clients/cad-desktop-helper/Helper.Tests/`;
- `.github/workflows/cad-helper-shared-dotnet.yml` update for Helper paths and
  build/test steps;
- `docs/DEV_AND_VERIFICATION_CAD_HELPER_BRIDGE_S3_HELPER_STARTUP_R1_20260521.md`;
- one `docs/DELIVERY_DOC_INDEX.md` line for the DEV/verification MD.

It should not modify S1 Shared or S2 Detector unless a narrowly scoped test
seam is required and is explicitly disclosed in the PR body. Any Shared or
Detector change must be behavior-preserving and justified as infrastructure for
testing S3, not as a hidden follow-up.

## 5. Mandatory Tests for the Implementation PR

The S3 implementation PR must include these exactly named tests or their
language-equivalent xUnit names:

1. `test_helper_binds_loopback_only_and_allocates_first_free_port`
2. `test_helper_never_binds_wildcard_or_random_port`
3. `test_healthz_is_bare_and_returns_expected_json_body`
4. `test_healthz_is_not_healthy_before_token_bootstrap_and_session_publish`
5. `test_session_file_schema_matches_shared_helper_session_file`
6. `test_session_file_uses_current_session_id_filename`
7. `test_session_file_publish_is_atomic_no_partial_final_file`
8. `test_normal_shutdown_deletes_current_session_file`
9. `test_bootstrap_creates_64_char_lowercase_hex_local_token`
10. `test_existing_local_token_is_reused_not_overwritten`
11. `test_bootstrap_failure_exits_without_publishing_session_file`
12. `test_mutex_name_uses_shared_install_id_and_local_namespace`
13. `test_second_instance_healthy_helper_exits_zero`
14. `test_missing_session_file_retries_then_singleton_lost`
15. `test_dead_pid_session_file_is_deleted_and_startup_retries`
16. `test_pid_reuse_image_path_mismatch_is_deleted_and_startup_retries`
17. `test_unhealthy_matching_process_does_not_delete_session_file`
18. `test_idle_timeout_stops_helper_and_deletes_session_file`
19. `test_config_idle_timeout_override_accepts_only_1_to_1440_minutes`
20. `test_no_s4_s7_s8_scope_leak`
21. `test_dotnet_workflow_covers_helper_paths_build_and_tests`

Recommended additional guards:

- source scan: no `MapGet` routes except `/healthz`;
- source scan: no `--reset-local-token`;
- source scan: no SQLite package/reference;
- source scan: no CADDedupPlugin path edits;
- path-filter scan proving workflow includes Helper and Helper.Tests.

## 6. Verification Commands

Expected Windows-capable verification for the implementation PR:

```bash
dotnet restore clients/cad-desktop-helper/Helper.Tests/Yuantus.Cad.Helper.Tests.csproj
dotnet build clients/cad-desktop-helper/Helper/Yuantus.Cad.Helper.csproj --configuration Release --no-restore
dotnet test clients/cad-desktop-helper/Helper.Tests/Yuantus.Cad.Helper.Tests.csproj --configuration Release --no-restore
```

The existing Windows workflow must also continue to run Shared and Detector:

```bash
dotnet test clients/cad-desktop-helper/Shared.Tests/Yuantus.Cad.Shared.Tests.csproj --configuration Release --no-restore
dotnet test clients/cad-desktop-helper/Detector.Tests/Yuantus.Cad.Detector.Tests.csproj --configuration Release --no-restore
```

Repository verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_odoo18_r2_portfolio_contract.py \
  src/yuantus/meta_engine/tests/test_tier_b_3_breakage_design_loopback_portfolio_contract.py
```

```bash
git diff --check
```

Local macOS can run doc-index and source-scan checks, but the merge gate for S3
must include a Windows .NET SDK run for Helper build/test.

## 7. DEV/Verification MD Requirements

The implementation PR must add:

```text
docs/DEV_AND_VERIFICATION_CAD_HELPER_BRIDGE_S3_HELPER_STARTUP_R1_20260521.md
```

The DEV/verification MD must document:

- exact files changed;
- S3 scope vs S4-S11 non-goals;
- how `/healthz` is the only endpoint owned by S3;
- token-bootstrap ordering proof;
- session-file atomic publish proof;
- singleton recovery proof for healthy, stale, PID-reuse, and unhealthy cases;
- idle-timeout policy and config fallback proof;
- dedicated Windows workflow run URL or run id for the implementation SHA;
- local verification limitations if `.NET SDK` is missing on the workstation.

## 8. Non-Goals

This taskbook is not an implementation authorization.

S3 implementation non-goals:

- No edits to `clients/autocad-material-sync/`.
- No edits to `plugins/`.
- No edits to Python service code.
- No database schema or migration.
- No tenant baseline changes.
- No CAD write behavior.
- No registry writes.
- No installer, repair, or auto-start behavior.
- No `--reset-local-token`.
- No S4 auth/origin, S5 session routes, S6 business routes/audit, S8 plugin
  migration, S9 bridge, S10 LISP shell, or S11 integration runbook.
- No CAD pool multi-server work.

## 9. Decision Gate / Handoff

Doc-only. Implementation may start only after:

1. this taskbook merges;
2. the user gives a separate explicit opt-in for
   `feat/cad-helper-bridge-s3-helper-startup-r1-20260521`.

Recommended branch name for the implementation PR:

```text
feat/cad-helper-bridge-s3-helper-startup-r1-20260521
```

Follow-ups after S3 remain:

- S4 auth/origin allowlist;
- S5 session/version/current-drawing endpoints;
- S6 business endpoints and audit;
- S7 reset-token CLI;
- S8 CADDedupPlugin migration;
- S9 LISP bridge;
- S10 ZWCAD/GstarCAD LISP shell;
- S11 integration and verification package.

Each remains its own explicit opt-in.

## 10. Reviewer Focus

- Confirm the `/healthz` carve-out: S3 owns only minimal unauthenticated
  `/healthz`; S5 still owns `/version` and session/CAD context routes.
- Confirm token-bootstrap ordering: no healthy response before DPAPI token write
  and session-file publish.
- Confirm singleton recovery matches #614 R3.2 exactly, especially the
  `HELPER_UNHEALTHY` no-delete branch.
- Confirm `config.json` support is limited to `idle_timeout_minutes` with safe
  fallback and does not grow into S5 session configuration.
- Confirm `.github/workflows/cad-helper-shared-dotnet.yml` must be updated by
  the implementation PR; S3 cannot rely on generic repository contracts for
  .NET coverage.
- Confirm no S4-S11 scope creep, especially no local-token enforcement and no
  `--reset-local-token`.
