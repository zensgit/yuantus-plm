# PLM-Collab V2 — Seats (per-license user limit): design for review

**Status:** design-only. No code in this PR. This is the `draft → review → build`
gate: review this, decide the one open fork (§4: Option A vs B), then S1 is built.

**Scope.** How a "seats" cap (a limit on how many users a paid feature covers) is
*modeled, counted, and enforced* for the collab SKU(s). Deliberately small and
in-repo. Out of scope, with reasons, in §5.

---

## 1. Key finding: seats is an EXTENSION of an existing spine, not greenfield

Yuantus already ships a tenant quota framework that does almost exactly what the
seats principles ask for. Grounding:

- **`TenantQuota`** — `src/yuantus/security/auth/models.py` (table `auth_tenant_quotas`,
  PK `tenant_id`, in the **identity DB**). Columns: `max_users`, `max_orgs`,
  `max_files`, `max_storage_bytes`, `max_active_jobs`, `max_processing_jobs` — all
  nullable, where **null = unlimited**.
- **`QuotaService(identity_db, *, meta_db=None)`** — `src/yuantus/security/auth/quota_service.py`:
  - `get_usage(tenant_id)` (L81–87) counts **active users** for the tenant:
    `count(AuthUser.id) where tenant_id == ? and is_active`.
  - `evaluate(tenant_id, deltas)` (L138–170) is **resource-name driven**: for each
    `resource` in the delta it compares `usage.<resource>` against
    `quota.max_<resource>`. Adding a new quota dimension = add `max_<x>` to
    `TenantQuota` + `<x>` to `QuotaUsage` + a count query. No new service.
  - `raise_if_exceeded(tenant_id, deltas)` (L172–178) raises `QuotaExceededError`
    **only in `enforce` mode**.
  - **`QUOTA_MODE`** (L55, L197–201): `disabled | soft | enforce`, default
    `disabled` → the whole framework **ships off** until a deployment opts in.
- **It is already enforced at provisioning**, not at a feature gate:
  `POST /admin/users` (`src/yuantus/api/routers/admin.py`, `create_user`) calls
  `QuotaService` with `{"users": 1}` **before** `AuthService.create_user(...)`.

This spine already embodies all four principles in the brief (enforce at
provisioning; `is_entitled()` untouched; cross-DB aware; extensible). **Seats =
one more resource dimension on this spine.** We are not inventing a mechanism.

---

## 2. The four questions, answered against the real code

### Q1 — License model: `seat_limit` on `AppLicense`, or an independent limits table?

The "independent limits table" **already exists** (`TenantQuota`, identity DB).
But the license (`AppLicense`, table `meta_app_licenses`) lives in the **meta DB**
(`src/yuantus/meta_engine/app_framework/store_models.py`). So:

- The **license stays the commercial source of truth** (vendor-signed; eventually
  carries a `seats` number — see §5/S2).
- The **enforceable limit lives identity-side** (on/near `TenantQuota`), in the same
  DB as the user count.
- Do **not** make the enforced number live *only* on `AppLicense`: that splits the
  limit (meta DB) from the count (identity DB) across the engine boundary — exactly
  the cross-DB counting hazard the brief warns about.

The remaining choice is *which* identity-side shape — reuse `max_users` vs add a
per-feature dimension. That is the one open fork: **§4**.

### Q2 — Count source: identity active users / provisioned MetaSheet users / feature-assigned users?

**Established source = identity active users** (`get_usage().users`). It is already
the basis of `max_users`, already same-DB as the limit, already battle-tested.

Two honesty notes that decide the design:

- **A per-feature *limit* over a tenant-wide *count* is not per-feature *seats*.**
  With the count = "active users in the tenant," a "collab seat limit" means *a
  per-license limit **number** applied to the tenant-wide user count* — it does
  **not** distinguish *which* users use collab. **True per-feature seats** (Alice
  has collab, Bob does not, each SKU its own roster) require a **user↔feature
  assignment table** as the count source — a new subsystem. Correctly **deferred**
  (§5). Limit granularity only means something if it matches count granularity;
  this design keeps both at tenant scope and is explicit that it does.
- **"Provisioned MetaSheet users" is consumer-side** (the metasheet2 service), a
  different process across the integration boundary. The provider cannot
  authoritatively count or enforce on the consumer's headcount; at best the
  consumer *reports* usage advisorily. Defer to the V1.2-embed era.

### Q3 — Enforcement point (derived from Q2, not a free choice)

Because the count source is **account existence** (an active `AuthUser`), a seat is
**consumed when the account is provisioned** — an account that never logs in still
holds a seat. Therefore the consumption event, and so the enforcement seam, is
**provisioning**, *by construction*:

- Enforce at the **provisioning seam** (user creation / activation), reusing
  `QuotaService.raise_if_exceeded(deltas={"<seat_resource>": 1})` — exactly how
  `max_users` is enforced today in `create_user`.
- **Login is the wrong seam** for a headcount model: a seat is already spent before
  first login, and login enforcement would only fit a *session/concurrency* seat
  model the brief did not ask for. At most a **soft advisory** at login (warn /
  audit), never a hard block.
- **Never** per-request feature-gate counting.

### Q4 — `is_entitled()` stays a pure feature check

No change. `is_entitled()` (`entitlement_service.py` L67–107) answers "does this
tenant hold an active, in-window license for the feature?" — one indexed query on
`meta_app_licenses` scoped by `resolve_license_scope()` (`license_scope.py` L16–37).
Seats are a **separate** `QuotaService` call at the provisioning seam. The two code
paths never touch; the seats work adds **zero** to the entitlement hot path.

---

## 3. Cross-DB boundary — resolved (the strongest property of this design)

`AuthUser`/`TenantQuota` live in the **identity DB**
(`IDENTITY_DATABASE_URL or DATABASE_URL`, `auth/database.py` L20–22); `AppLicense`
lives in the **meta DB** (`DATABASE_URL`). Default: same URL → same DB. Split: set
`IDENTITY_DATABASE_URL`.

- **Enforcement is single-DB.** Both the limit and the count sit identity-side, so a
  seat check at provisioning needs only the **identity session** — identical to
  today's `max_users` check (`QuotaService(db)` in `create_user`, `db` = identity).
- **The boundary is crossed exactly once: at license import.** Projecting the
  license's seat number → identity-side limit is one controlled, infrequent
  **write**, never a hot-path join. (S2; see §5 on its coupling to issuance.)
- The design holds in **both topologies** (same-DB and split) because enforcement
  never joins meta↔identity.

---

## 4. The one decision that gates the build: Option A vs B

|  | **A — reuse tenant-wide `max_users`** | **B — per-feature seat dimension** *(recommended)* |
|--|--|--|
| Schema change | none | +1 dimension: `max_collab_users` on `TenantQuota` (or a `feature_seat_limits(tenant_id, feature_key, max_seats)` row), identity DB |
| Meaning | total tenant users **is** the cap | a per-SKU limit **number** over the tenant user count |
| Multi-SKU | conflates all SKUs into one cap | each SKU keeps its own seat number |
| Admin clobber | projecting a license seat count into `max_users` would **overwrite an admin's manually-set tenant cap** | separate dimension — no clobber |
| Best when | collab is effectively the only seat-metered product | you sell multiple feature SKUs with distinct seat tiers |

**Recommendation: B.** There are 5 feature SKUs (`plm.collab`,
`plm.approval_automation`, `plm.bom_multitable`, `plm.ecm_publish`,
`plm.cadpdm_date_obsolete`); a per-feature seat number keeps each SKU's commercial
terms independent and avoids clobbering an admin-set `max_users`. **A** is a
legitimate cheaper cut **if** collab is the only thing you ever meter by seats.

> B as scoped here is a per-feature **limit** over a tenant-wide **count** (see Q2).
> Distinct users *per* SKU is the deferred assignment subsystem, not this fork.

---

## 5. Deferred — named, with reasons (not silently dropped)

- **User↔feature assignment subsystem** (true per-SKU distinct-user seats): a new
  model + lifecycle + admin UI. Only needed for *sub-tenant* seat allocation. Until
  then, seats are tenant-scoped (§2) and honest about it.
- **License `seats` payload + import-time projection** (S2): the seat number belongs
  in the **vendor-signed** license payload (tamper-evident, Ed25519, already imported
  via `LicenseImportService`). But minting a seat-bearing license touches the
  **vendor-private issuance tool**, which is out of clean in-repo scope. The design
  *names* the license as eventual source of truth; the **build does not lead with
  it** (see §6).
- **MetaSheet-consumer seat reconciliation**: cross-service, V1.2-embed-era,
  advisory at best.
- **Admin seat UX**: no Yuantus frontend exists; surface limits via API/CLI only.
- **multi-kid**: V1.2-embed-gated, unchanged from the prior ladder note.

---

## 6. Build plan (after this review; ordered for clean in-repo cuts)

- **S0 — this doc.** Design + the A/B decision. ← **review gate.**
- **S1 — first buildable slice, fully in-repo, ships default-off.** Add the
  identity-side seat dimension (per the decided option) + its count query (reuse
  `get_usage()` for tenant-wide), and **enforce at the provisioning seam** via a
  `QuotaService` delta, gated by `QUOTA_MODE` (disabled by default). Tests: usage
  count, `evaluate`/`raise_if_exceeded`, default-off, soft vs enforce, null =
  unlimited. **No license payload yet.**
- **S2 — source-of-truth handshake.** Project the license seat number → identity-side
  limit at import. Sequenced **with** the vendor-private issuance tool (seat-bearing
  license), not as the first cut.
- **S3 — deferred.** Assignment subsystem / consumer reconciliation, only if/when
  sub-tenant or embed seats are actually required.

---

## 7. Invariants to carry forward

1. `is_entitled()` stays a pure feature check — seats never enter the entitlement hot path.
2. Enforce **only** at provisioning; default-off via `QUOTA_MODE`; null limit = unlimited.
3. License = commercial source of truth; the identity-side limit is the enforcement
   cache, in the **same DB as the count**.
4. No cross-DB join on any hot path; the **only** cross-boundary hop is the
   import-time projection write (S2).
5. Tenant-scoped seats are explicitly a per-feature *limit over a tenant-wide count*
   until the assignment subsystem (S3) lands — never overstated as distinct-user seats.
