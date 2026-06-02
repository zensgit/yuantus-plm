# DESIGN — Publish Released Versions to ECM Controlled-Record Repository (Phase 0 + Phase 1)

> Status: **DESIGN R3 — Phase 0 gate PASSED (execution still required); Phase 1 pre-implementation nails closed** · Date: 2026-06-02 · Branch: `claude/ecm-publish-phase01`
>
> One line: when a Yuantus item version enters **Released**, publish its **controlled files** (drawing / spec PDF) to **Athena ECM** as versioned document nodes carrying PLM metadata + a back-link — one-directional, event-triggered, **never able to fail a core release**, near-zero change to Athena.

---

## 0. Revision History

**R3 (2026-06-02) — 5 pre-implementation nails + D6 locked:**

| Nail | Change |
|---|---|
| Conflict must not throw into `release()` | New **terminal reason `CONFLICT`**. Changed-fingerprint-after-`SENT` is **recorded** as a `SKIPPED/CONFLICT` audit row (surfaced via outbox state/property), **never raised** — diverging from ERP's `PublicationConflictError` *because our call site is inside `release()`*. (§2, §6, §8) |
| Folder resolution contradiction | Split: **enqueue** resolves only the static **tenant *base* folder** (no I/O); the **worker** remotely `createFolder` `Released/<part-number>` and writes the final `athena_folder_id` + `athena_object_id` back to `snapshot`. (§3, §6, §7) |
| `FileContainer.checksum` is nullable | Fingerprint **fallback** when checksum is null: `sha256(file_id | system_path | file_size | mime_type | generation | revision | file_role | plm-meta)` — still **no byte read**, still non-blocking. (§2, §6) |
| `release()` must set `released_by_id` too | `release_version()` sets **both** `released_at` *and* `released_by_id = user_id` (fields exist; the `change_service` path already sets them, `release()` did not). (§6) |
| `_release_version` delegation is version-semantic | Extract a single choke point **`VersionService.release_version(version_id, user_id)`**; `release(item_id)` resolves the current version → `release_version`; `change_service._release_version(version_id)` delegates to `release_version` **for that specific version** (no mis-release of the current version). The ECM enqueue hook lives in `release_version` so **both** paths publish the **correct** version. (§3, §4, §6) |
| **D6 LOCKED** | Multiple governing ECOs → eligible iff **ALL ∈ {approved, done}** (conservative; fits "controlled record"). Parallel-ECO exceptions handled later by process rule, not code. |

**R2 (2026-06-02):** non-blocking enqueue contract; outbox carries tenant; bare Phase-0 property keys; SENT terminal; ECO gate queries all; `_release_version` elevated from out-of-scope. **Owner 拍板 (R2):** D1 ✓ · D2 ✓ · tenant=PluginConfig+snapshot ✓ · allowlist ✓ · Phase 0 first ✓.

---

## 1. Scope & Naming

**"PLM publishes released versions to the ECM controlled-record repository."** NOT "bidirectional", NOT "unified file store."

**In scope (Phase 1):** publish controlled files on version Release (ECO-gated); CMIS push with PLM metadata + back-link; durable async delivery (outbox + worker + retry) modeled on `erp_publication`; capability **entitlement-gateable** from day one.

**Out of scope (deferred — new gate required):** disposition (supersede/withdraw — *ECM record goes stale otherwise; Phase 3+*); bidirectional read-back; mail→PLM; full store delegation; the monetization system (separate taskbook, §11).

**System-of-record split:** Yuantus holds the working/native copy; Athena becomes the **controlled record** (versioned, searchable, retainable, distributable).

---

## 2. Decisions (all accepted)

| # | Decision | Reasoning |
|---|----------|-----------|
| **D1** | Parallel **`ecm_publication`** module; do not reuse the shared ERP table. | ECM pushes file bytes+metadata via CMIS; ERP pushes a readiness verdict. |
| **D2** | Trigger = `VersionService.release_version()`; the publish path **cannot fail the release** (contract below); ECO check is **eligibility** (skip+audit), never a veto. | `release_version()` runs inside the lifecycle txn. |
| **D3** | Idempotency key `(item_id, version_id, file_id, file_role, target_system)`. | Same role can carry different files. |
| **D4** | Allowlist `drawing` + PDF `attachment`; exclude `native_cad`; `preview`/`geometry` off; + MIME guard. | Only distributable controlled copies. |
| **D5** | Athena **CMIS Browser**; **Keycloak** service account; **entitlement-gateable** as `plm.ecm`. | CMIS is Athena's verified write path. |
| **D6** | Multiple governing ECOs → eligible iff **ALL ∈ {approved,done}**. | Conservative; fits controlled-record. |

### The enqueue contract (how D2 is *guaranteed*)

`EcmPublicationOutboxService.enqueue_release(item, version, user_id)` MUST, by construction:
1. **No remote calls** — DB inserts only. All HTTP (token, createFolder, createDocument, content) is in the worker.
2. **No file byte reads** — fingerprint uses the pre-computed `FileContainer.checksum` (SHA256); **fallback when null** = `sha256(file_id | system_path | file_size | mime_type | generation | revision | file_role | plm-meta)`. Never calls `FileService.download_file`.
3. **Total / never raises into `release_version()`** — missing entitlement / tenant mapping / base folder, zero controlled files, **or a post-SENT fingerprint conflict** all resolve to a **`SKIPPED`** row (`reason ∈ {NOT_ELIGIBLE, CONFIG_MISSING, CONFLICT, VALIDATION_ERROR}`) or no-op. **Conflict is recorded, not thrown.**
4. **Crash-safe persist** — insert wrapped in **`session.begin_nested()`** (SAVEPOINT; precedent `numbering_service.py:397`); on DB error the savepoint rolls back and the release still commits. Caller also guards `try/except` + log.

Outbox **reasons**: `NOT_ELIGIBLE | CONFIG_MISSING | CONFLICT | ADAPTER_ERROR | REMOTE_ERROR | VALIDATION_ERROR`. `CONFLICT`/`NOT_ELIGIBLE`/`CONFIG_MISSING`/`VALIDATION_ERROR` are terminal (no retry); `ADAPTER_ERROR`/`REMOTE_ERROR` retry with backoff.

---

## 3. Architecture

```
[Yuantus]                                                  [Athena ECM]   (no change)
 LifecycleService.promote_to_state("Released") ─► release(item_id,user) ─┐
 change_service._release_version(version_id,user) ──────────────────────┴─► VersionService.release_version(version_id, user)
        │  (single choke point; inside the lifecycle/request DB txn)
        ├─ mark version Released (+ set released_at AND released_by_id=user)
        └─ if EntitlementService(session).is_enabled("plm.ecm"):          ← no-op True in dev
             try:
               with session.begin_nested():                              ← SAVEPOINT; cannot break release
                 EcmPublicationOutboxService(session).enqueue_release(item, version, user)
                   ├─ tenant/org ← request context  → store on row
                   ├─ athena_tenant_id + athena_BASE_folder_id ← static mapping → snapshot
                   │     (missing → SKIPPED/CONFIG_MISSING, no throw; NO remote createFolder here)
                   ├─ ECO gate: ALL ECOs(target_version_id==version.id) ∈ {approved,done}?
                   │     (snapshot eco_ids+states; else SKIPPED/NOT_ELIGIBLE)
                   ├─ controlled files (allowlist + MIME guard)
                   └─ per file: fingerprint (checksum or fallback, NO bytes);
                        new identity → PENDING;
                        same fingerprint → no-op;
                        changed fingerprint vs a SENT row → SKIPPED/CONFLICT (recorded, NOT thrown)
             except Exception: log    # release proceeds regardless
                     ▼  (rows commit with the release — transactional outbox)
 EcmPublicationOutboxWorker.run_once()   (claim FOR UPDATE SKIP LOCKED; no request context)
   └─ AthenaCmisAdapter.send(row)   (reads tenant + base folder from snapshot)
        ├─ AthenaClient: Keycloak client-credentials token (cached)   ──► Keycloak /token
        ├─ FileService.download_file(file.system_path)                ← bytes read HERE
        ├─ CMIS createFolder  Released/<part-number>  (lazy)          ──► …?cmisaction=createFolder
        ├─ CMIS createDocument (folder=that, BARE props)              ──► …?cmisaction=createDocument
        ├─ CMIS setContentStream (base64)                             ──► …?cmisaction=setContentStream
        ├─ (checkIn iff Phase-0 proves it's needed for a version)     ──► …?cmisaction=checkIn
        └─ SENT + write final athena_folder_id + athena_object_id to snapshot; errors → backoff/dead-letter
```

---

## 4. Verified Code Anchors (read 2026-06-02; lines may drift)

**Hook & domain (Yuantus):**
- `version/service.py:466` `def release(self, item_id, user_id)` — **R3: extract `release_version(self, version_id, user_id)` as the choke point**; `release(item_id)` resolves `item.current_version_id` → `release_version`. The body must additionally set `released_at` **and** `released_by_id` (both currently unset by `release()`; the fields exist — `change_service._release_version` sets them).
- `lifecycle/service.py:270-279` `if … "Released" … ver_svc.release(...)` (owns txn).
- `services/change_service.py:118 → :132 _release_version(version_id, user_id)` — **R3: delegate to `release_version(version_id, user_id)`** (same specific version; no mis-release).
- `models/eco.py:47 ECOState`, `:163 source_version_id`, `:166 target_version_id` (both non-unique FK → multiple ECOs per version).
- `version/models.py:29 VersionFileRole`; `:114 version_files`; `:207 uq_version_file_role`.
- `models/file.py:104-105 checksum (SHA256, NULLABLE)` — primary fingerprint source; §2 fallback when null.
- `services/file_service.py:82 download_file` (worker only).
- Item has **no** tenant/org column → tenant from request context.

**Template & precedent (Yuantus):** `erp_publication/{models.py:58, service.py:135/217, worker.py:49, adapter.py:42}`; SAVEPOINT precedent `numbering_service.py:397`; alembic `migrations/versions/erp_pub_outbox_001_*.py`.

**Auth/config (Yuantus):** `integrations/athena.py:75 AthenaClient`; `config/settings.py ATHENA_*`.

**Athena (verified from source):** `CmisBrowserController.java:35 {/api/cmis/browser,/api/v1/cmis/browser}`, `:88 cmisaction`, `:159 createDocument`, `:162 setContentStream`, `:164 checkIn` (+ `createFolder` handled in the same switch). JWT→Keycloak `realm_access.roles`; `X-Tenant-ID`→tenant root; `properties.<key>` indexed.

---

## 5. Phase 0 — Verification Kit (design gate PASSED; **execution still required** before Phase 1 coding)

**Unknowns to pin:** **U1** which Keycloak **realm role** Athena accepts for CMIS write · **U2** the version-producing **call sequence** (2 vs 3 calls; does `checkIn` need `checkOut`) · **U3** **bare** property keys searchable as `properties.plm_part` (createDocument stores raw; updateProperties strips `athena:property.*`) · **U4** `X-Tenant-ID` + folder routing · **U5 (R3)** `createFolder` for a sub-path works with the same token/tenant.

**Canonical Phase 0 execution = `scripts/ecm_publish_phase0/smoke.py`** (with its `README.md` / `.env.example`). It supersedes any inline snippet: the token is never printed, the two versioning paths use **two separate documents**, folders nest as `Released-<run>/<part>`, and U3 searchability is confirmed **manually** via Athena's Node/Search API. **Do not use an abbreviated inline snippet as implementation guidance.**

**Acceptance (gate to Phase 1 coding):** a **versioned** doc with content + 3 **bare** props, readable + **searchable by `properties.plm_part`**, plus a **sub-folder created**, all via a **Keycloak service-account token** + `X-Tenant-ID`. Record in `VERIFICATION_…_PHASE0.md`: winning **sequence**, required **realm role**, **property key path**, **createFolder** recipe.

---

## 6. Phase 1 — File-Level Change Plan

**New `src/yuantus/meta_engine/ecm_publication/`:**

- **`models.py`** — `EcmPublicationOutbox` (`meta_ecm_publication_outbox`). Mirror `ErpPublicationOutbox` **plus** `file_id`, `file_role`, `tenant_id`(indexed), `org_id`. UniqueConstraint `(item_id, version_id, file_id, file_role, target_system)`. States `PENDING|SENT|FAILED|SKIPPED`; reasons per §2 (incl. `CONFLICT`). `snapshot`: `athena_tenant_id`, `athena_base_folder_id` (enqueue), `athena_folder_id` + `athena_object_id` (worker), `eco_ids`, `eco_states`, `released_by`, `fingerprint_basis` (`"checksum"` | `"fallback"`), `filename`, `mime_type`, `file_size`.

- **`service.py`** `EcmPublicationOutboxService`:
  - `enqueue_release(item, version, user_id)` — implements §2 contract under `begin_nested()`. Order: tenant/org from context → resolve `athena_tenant_id` + **base** folder (static map; missing → `SKIPPED/CONFIG_MISSING`) → ECO gate (all-final, D6) → controlled files → per file: compute fingerprint (checksum or fallback), then **dedupe/conflict** vs existing row of the same identity: new → `PENDING`; same fp → no-op; changed fp & prior `SENT` → `SKIPPED/CONFLICT` (recorded). **No createFolder, no byte read here.**
  - Reuse erp `reschedule_retry`.

  ```python
  ecos = session.query(ECO).filter(ECO.target_version_id == version.id).all()
  eligible = (not ecos) or all(e.state in {ECOState.APPROVED.value, ECOState.DONE.value} for e in ecos)
  fp = file.checksum or sha256_of(file.id, file.system_path, file.file_size, file.mime_type,
                                  version.generation, version.revision, vf.file_role, plm_meta)
  ```

- **`adapter.py`** `AthenaCmisAdapter.send(row)` — read tenant + `athena_base_folder_id` from snapshot; lazy `createFolder Released/<part>`; `createDocument`(bare props) → `setContentStream` → (`checkIn` per Phase 0); write `athena_folder_id` + `athena_object_id` back; exception→adapter_error, non-2xx→remote_error.

- **`worker.py`** `EcmPublicationOutboxWorker` (copy `PublicationOutboxWorker`).

**`integrations/athena.py`** — add `cmis_create_folder`, `cmis_create_document`, `cmis_set_content_stream`, `cmis_check_in` to `AthenaClient` (reuse auth + breaker).

**`migrations/versions/ecm_pub_outbox_001_*.py`** — create the table (template `erp_pub_outbox_001`).

**`version/service.py` (R3 refactor):**
```python
def release(self, item_id, user_id):
    item = ...; return self.release_version(item.current_version_id, user_id)

def release_version(self, version_id, user_id):          # the choke point
    ver = ...; 
    if ver.is_released: return ver
    # ... existing lock checks ...
    ver.is_released = True; ver.state = "Released"
    ver.released_at = datetime.utcnow(); ver.released_by_id = user_id   # R3: set BOTH
    # ... release file locks, log ...
    item = self.session.query(Item).get(ver.item_id)
    if EntitlementService(self.session).is_enabled("plm.ecm"):
        try:
            with self.session.begin_nested():
                EcmPublicationOutboxService(self.session).enqueue_release(item, ver, user_id)
        except Exception:
            logger.exception("ecm enqueue skipped; release unaffected")
    return ver
```

**`services/change_service.py` (R3):** `_release_version(version_id, user_id)` → `VersionService(self.session).release_version(version_id, user_id)` (specific version; no current-version mis-release).

**`config/settings.py`** — `ECM_PUBLISH_ROLES={"drawing"}`, `ECM_PUBLISH_MIME_ALLOW`, worker tunables, tenant→**base folder** mapping (PluginConfig key).

---

## 7. Tenant / Identity / Folder Mapping

- **Tenant on the row:** Item has no tenant; `enqueue_release` reads tenant/org from request context, persists `tenant_id`/`org_id`, resolves `athena_tenant_id` + **base folder** into `snapshot`. Worker uses the row only.
- **Folder split (R3):** enqueue resolves the static **tenant base folder** (no I/O); the **worker** does the remote `createFolder Released/<part-number>` and records the final `athena_folder_id`. This keeps enqueue I/O-free *and* removes the §3/§7 contradiction.
- **Mapping store:** PluginConfig/small config (owner-accepted): Yuantus tenant(/org) → `X-Tenant-ID` + base folder node id.
- **Identity:** publish runs as a **service principal**; the real PLM user (`released_by_id`) rides along as a bare property. Per-user SSO is out of scope.

---

## 8. Idempotency, Conflict, Re-release (Phase 1)

- First publish: identity absent → `PENDING` → worker → `SENT` (+ `athena_object_id`).
- Re-enqueue same fingerprint: idempotent no-op.
- Re-enqueue changed fingerprint while prior is `SENT`: **`SKIPPED/CONFLICT`** — a terminal audit row surfaced via the outbox (queryable / dashboardable), **never raised into `release_version()`**. Ops decides; no silent overwrite, no auto-version.
- Deferred (not Phase 1): "new content as a new CMIS version of the existing `athena_object_id`" — needs `ecm_publication_links` + the Phase-0 checkIn semantics.

---

## 9. Risks & Honest Caveats

- **CMIS shape unverified until Phase 0 execution** — §5 must run first.
- **checksum null** — fallback fingerprint (§2) is weaker for content-only changes that keep size/mime/rev; acceptable for v1, `fingerprint_basis` records which was used.
- **CONFLICT surfacing is async/ops, not an exception** — a changed-after-SENT publish needs an operator action (or the deferred re-version feature); it will sit as a `SKIPPED/CONFLICT` row, not error the release.
- **Disposition gap** — Phase 3+.
- **SAVEPOINT validity** — used in-repo (`numbering_service.py:397`); a Phase-1 test simulates an enqueue failure and asserts the release still commits.
- **base64 (CMIS Browser)** — fine for controlled docs.

---

## 10. Test Plan

- `test_ecm_publication_outbox_service.py` — fingerprint from checksum (**assert `download_file` NOT called**) **and** the null-checksum fallback path; ECO gate with **multiple** ECOs (mixed → not eligible); allowlist; `CONFIG_MISSING` (no mapping → SKIPPED, no throw); **`CONFLICT` recorded not raised** (changed fp after SENT → SKIPPED/CONFLICT, no exception).
- `test_release_nonblocking.py` — `release_version()` no-op when not entitled; sets `released_at` **and** `released_by_id`; **simulated enqueue error → release still commits**.
- `test_release_version_semantics.py` — `release(item_id)` releases the current version; `_release_version(version_id)` (post-refactor) releases **that** version (not necessarily current) and both enqueue the correct version.
- `test_ecm_publication_outbox_worker.py` — claim/process; `createFolder`→`createDocument`→content; retry on remote_error; dead-letter; `athena_folder_id`+`athena_object_id` written on SENT.
- Adapter contract test (httpx mock) — Phase-0 sequence + bare keys + error classification.

---

## 11. Forward Hook: Entitlement-Gateability (seam only)

Phase 1 ships `EntitlementService(session).is_enabled(app_name)` returning **True** (no-op), ECM router + the `release_version()` enqueue behind it / `require_app("plm.ecm")`. The real entitlement system (vendor-**signed** offline-verifiable token; online/offline activation; billing; ship-dormant provisioning) is a **separate "Online Upgrade / Paid ECM" taskbook**. The seam now makes that a flag-flip, not a refactor.

---

## 12. Open Questions for Re-gate

1. **Folder pre-provisioning (§7)** — who creates each tenant **base** folder, and is `Released/<part-number>` the agreed sub-path?
2. **Phase 0 infra** — owner's Docker / staging? Who creates the Keycloak service-account client + the test tenant folder?

**Resolved:** D1–D6 ✓ · non-blocking contract (no throw incl. CONFLICT) ✓ · tenant on row + base-folder split ✓ · checksum fallback ✓ · `release_version` choke point + `released_by_id` ✓ · `_release_version` delegation (version-specific) ✓ · Phase 0 **design** gate ✓ (execution pending).
