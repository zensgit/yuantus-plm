# DESIGN — Online Upgrade / Paid ECM Entitlement (on-prem PLM, online-upgradable)

> Status: **DESIGN R2 — direction accepted; security nails added; NOT yet gate-to-build** · Date: 2026-06-02 · Branch: `claude/ecm-publish-phase01`
>
> One line: let an **on-prem** Yuantus PLM unlock the **ECM** capability when a user pays — without sending the customer's data off-prem. Only a small **vendor-signed entitlement token** travels.
>
> Separate from `DESIGN_ECM_PUBLISH_RELEASE_TO_ECM_PHASE01_20260602.md` (that builds the ECM *capability*; this gates it). Kept independent on purpose.

---

## 0. Revision History

**R2 (2026-06-02) — 6 security nails before this is gate-to-build:**

| Nail | Change |
|---|---|
| Key rotation | Token header carries **`kid`**; on-prem holds a **keyring** (kid→public key), not one key. Verification **pins `algorithms=["EdDSA"]`** (or RS256) and **rejects `none`/any `HS*`** (alg-confusion defense). (§4 E7, §5, §6) |
| `license_key` too small for a JWS | `license_key` is `String(100)` (`store_models.py:49`). Add `signed_token Text`, `token_hash`, `verified_at`, `last_verification_error`; `status`/`expires_at` become **display cache only**. (§2, §6) |
| Mock purchase must not bypass the gate | With `ENTITLEMENT_ENFORCE=true`, the mock `/purchase` must **not** mint a usable license, and install **and** runtime must require signed-token verification. DB `status='Active'` alone never entitles. (§4 E3, §6) |
| Activation hardening | `POST /api/store/activate` is **`require_platform_admin`** (store_router is **auth-less today**). The `.lic`/JWS is **never logged or echoed**; responses return only `{app, plan, exp, jti, verified, error?}`. Under enforce, `/purchase` + `/install` get the same admin guard. (§6) |
| Instance id | `sub` binds to a **stable `install_id`** generated at first boot and persisted (survives backup/migration) — **not** a hardware fingerprint (which false-locks on reinstall/migration/DR). (§4 E8, §5, §6) |
| `is_enabled()` never throws | Corrupt/expired/unverifiable token → **return `False` + record a diagnostic**, never raise into a business path. Mirrors the publish R3 non-blocking contract (not entitled → just don't enqueue; release is unaffected). (§6) |

**Accepted (owner):** keep separate from ECM publish ✓ · M1 offline-license-first ✓ · "not airtight DRM" framing ✓ · App-Store `status` is mock, not a trust source (`store_service.py:116`) ✓ · HS256 (`jwt.py:24`) unusable for entitlement ✓.

---

## 1. Scope & honest headline

**In scope:** make ECM a paid capability an on-prem instance can activate online/offline; the runtime **gate**; the **signed-license** mechanism (with rotation); **ship-dormant** provisioning.

**Out of scope:** the ECM capability itself (other taskbook); airtight DRM (impossible on a customer-owned box — §7); per-user PLM↔ECM SSO.

**Honest headline (verified):** Yuantus has an in-app App Store **skeleton** (real models/endpoints/install flow) but its licensing is an explicit **mock**, and the only repo crypto is hand-rolled **symmetric HS256** — unusable for licensing. The security-critical parts (asymmetric signing + rotation, runtime gate, activation, provisioning) are **greenfield on a good skeleton**.

---

## 2. What exists vs. what must be built (verified 2026-06-02)

| Layer | Exists (reuse) | Gap (build) |
|---|---|---|
| Catalog / license model | `store_models.py`: `MarketplaceAppListing` (`meta_store_listings`), `AppLicense` (`meta_app_licenses`: `license_key String(100)`, `plan_type`, `expires_at`, `status`, `license_data`), `AppRegistry` | **`signed_token Text`, `token_hash`, `verified_at`, `last_verification_error`** columns; `status`/`expires_at` demoted to cache |
| Store API | `web/store_router.py`: `/api/store/{sync,apps,purchase,install}` — **currently auth-less** (`Depends(get_db)` only) | `/api/store/activate`; **admin guard** (`require_platform_admin`) on activate (+ purchase/install under enforce) |
| License check | `store_service.py:116` install-time `AppLicense.status=='Active'` (mock; `purchase_app` mints `uuid4`; `expires_at` never checked) | **signature + claim verification**, runtime gate, enforce-disables-mock |
| Crypto | hand-rolled **HS256** `security/auth/jwt.py:24` (symmetric) | **asymmetric** verify (EdDSA/RS256) + **keyring/`kid`** + **alg-pinning** (reject `none`/`HS*`) — new dep |
| Gate pattern | guard idiom `services/suspended_guard.py`, `latest_released_guard.py` | `EntitlementService.is_enabled()` (never throws) + `require_app("plm.ecm")` |
| Admin auth | `require_platform_admin` (used across `api/routers/admin.py`) | apply to activation |
| Provisioning | compose SKU overlays `docker-compose.profile-{base,collab,combined}.yml` | dormant **ECM/Athena** profile |
| Gate seam | **already shipped** by publish R3: `is_enabled("plm.ecm")` no-op `True` | swap in real verification |

---

## 3. Architecture — data stays on-prem; only a signed token travels

```
  VENDOR CLOUD (you)                              CUSTOMER ON-PREM (their box, their data)
  ┌──────────────────────────────┐               ┌────────────────────────────────────────────┐
  │ Billing (Stripe)             │               │ Yuantus PLM                                 │
  │ Entitlement service          │  signed JWS   │  ├ first boot → stable install_id (persisted)│
  │  └ PRIVATE key(s), each kid  │── token ─────►│  ├ "Upgrade ECM" → cloud checkout (+install_id)│
  │                              │ (online poll  │  ├ /api/store/activate [admin] → verify       │
  │ PUBLIC keyring (kid→pubkey)  │  or .lic file)│  │   (keyring by kid, alg=EdDSA, exp, sub==id) │
  │  ships embedded in product   │               │  ├ EntitlementService.is_enabled (never throws)│
  └──────────────────────────────┘               │  ├ require_app("plm.ecm") gates ECM routes +  │
        rotate keys by adding a new kid           │  │   the release() publish hook                │
        (old kid still in the keyring)            │  └ ECM (Athena) stack: SHIPPED DORMANT          │
                                                  └────────────────────────────────────────────┘
```

---

## 4. Decisions (proposed — for gate)

| # | Decision | Reasoning |
|---|----------|-----------|
| **E1** | **Extend** the App Store framework. | Skeleton/UX exist; the gap is verification, not plumbing. |
| **E2** | License = vendor-signed **JWS (EdDSA/RS256)**, verified offline by an embedded **public** keyring; gate trusts the **signature + claims**, never DB `status`. | On-prem customer owns the DB; HS256/DB-boolean is self-forgeable. New asymmetric dep required. |
| **E3** | **`ENTITLEMENT_ENFORCE`** flag: when true, mock purchase grants nothing; install+runtime require a verified token. Default **false** (OSS/dev unchanged). | A mock that mints usable licenses makes the gate meaningless. |
| **E4** | **Dual activation** (online poll + offline `.lic`). | Air-gapped customers need the offline path. |
| **E5** | **Ship-dormant** provisioning via compose SKU profile. | Keeps data on-prem, air-gap-safe. *Not* zero-footprint — the bits ship and lie dormant. |
| **E6** | **Instance-wide** entitlement (no `tenant_id`) for the on-prem single-instance case. | Per-tenant only if they host multi-tenant — defer. |
| **E7** | **Key rotation built in:** `kid` header + on-prem **keyring**; verification **pins** the asymmetric alg and **rejects `none`/`HS*`**. | The first private-key rotation must not brick fielded installs; alg-pinning blocks the classic JWT alg-confusion attack. |
| **E8** | `sub` = **stable `install_id`** (first-boot, persisted, migration-survivable), **not** a hardware fingerprint. | Hardware FP false-locks on reinstall/migration/DR. |

---

## 5. The signed license (token shape)

A compact JWS (`.lic`). **Header:** `{ "alg": "EdDSA", "kid": "<key id>", "typ": "JWT" }`. **Claims:**

```
{
  "iss":  "yuantus-licensing",
  "sub":  "<install_id>",              // stable, persisted; NOT a hardware fingerprint
  "apps": ["plm.ecm"],
  "plan": {"plm.ecm": "Enterprise"},
  "nbf":  <issued>, "exp": <expiry>,   // expiry IS enforced
  "grace_days": 14,                    // post-expiry policy (read-only/grace)
  "jti":  "<license id>"               // revocation handle if ever needed
}
```

**Verification (on-prem), in order, all offline:**
1. parse header → look up `kid` in the **public keyring**; unknown kid → fail.
2. verify signature with **`algorithms=["EdDSA"]`** (or RS256) — **reject `none` and any `HS*`**.
3. check `nbf`/`exp` (+ `grace_days`).
4. `sub == this install_id`.
5. requested app ∈ `apps`.

**Storage:** raw token in `signed_token`; `token_hash`=sha256(token) for audit/dedup without logging the token; `verified_at`, `last_verification_error` for diagnosis; `status`/`expires_at` = derived display cache only.

---

## 6. On-prem build (this repo)

- **`security/entitlement/keyring.py`** — load the embedded **public keyring** (`kid → public key`); rotation = ship a new kid, keep old ones until all licenses re-issued.
- **`security/entitlement/verify.py`** — `verify_license(token, keyring) -> Entitlement | None`. New dep (`PyJWT[crypto]` EdDSA, or `cryptography`). **Pin algorithms; reject `none`/`HS*`.** Pure, total, returns `None` on any failure (never raises).
- **`security/entitlement/service.py`** — `EntitlementService(session).is_enabled(app_name) -> bool`: load `signed_token` → `verify_license` → check `install_id`/exp/app. **Catches everything; returns `False` + writes `last_verification_error`; never raises** (same spirit as publish R3's non-blocking enqueue). This is the `is_enabled` the publish taskbook already calls (no-op `True` today).
- **`api/dependencies/entitlement.py`** — `require_app(app_name)` (guard idiom) → 402/403 when not entitled; on ECM routers + surfaced to UI.
- **`web/store_router.py`** — `POST /api/store/activate` with **`Depends(require_platform_admin)`**: accept a `.lic`/fetched token → verify → persist (`signed_token`,`token_hash`,`verified_at`) → refresh `AppLicense`/`AppRegistry` cache. **Never log or echo the token**; return only `{app, plan, exp, jti, verified, error?}`. Under `ENTITLEMENT_ENFORCE`, also guard `/purchase` + `/install` and make mock `/purchase` grant nothing usable.
- **`security/entitlement/install_id.py`** — first-boot generation + persistence of a stable `install_id` (DB row / config), preserved across backup/migration; expose to the UI so checkout can carry it.
- **Migration** — `meta_app_licenses` += `signed_token`, `token_hash`, `verified_at`, `last_verification_error`.
- **Settings** — `ENTITLEMENT_ENFORCE` (default false), `ENTITLEMENT_PUBLIC_KEYRING(_FILE)`, `ENTITLEMENT_LICENSE` (offline), `ENTITLEMENT_ACTIVATION_URL` (online poll).
- **UI** — "Upgrade ECM": when `!is_enabled`, show the CTA (→ cloud checkout, carrying `install_id`) + an **offline `.lic` import** box; re-check after activation.

**Cloud side (separate component, not this repo):** billing + a signing service holding the **private** keys (one per `kid`), signing tokens on payment and serving them to the polling instance. Defined by the §5 contract.

---

## 7. Threat model — honest (it's the customer's box)

- **Stops:** casual unlock-without-paying (can't forge a vendor signature), expired use (expiry now checked), **alg-confusion / `alg:none`** (pinned + rejected), DB-status tampering (status is not the trust source).
- **Does NOT stop:** a determined host owner patching the binary / stubbing `is_enabled`. On-prem licensing = **raise the cost of cheating**, not airtight DRM. Bind to `install_id`; optional phone-home telemetry for *visibility* only (never a hard runtime dependency — would break air-gap). Contracts carry the rest.

---

## 8. Phasing (M1 = the wedge; includes the security nails)

- **M0 — gate seam** *(shipped by publish R3)*: `is_enabled` no-op `True`. Nothing to do.
- **M1 — offline signed license (build first):** keyring+`kid`+alg-pinning, `verify`, real `EntitlementService` (never throws), new license columns, `/api/store/activate` (admin, redacted), `install_id`, `require_app` behind `ENTITLEMENT_ENFORCE`, enforce-disables-mock. **No billing, no cloud** — you sign a `.lic` manually/CLI and hand it over. Forgery-resistant + air-gap-friendly.
- **M2 — online activation + billing:** Stripe checkout + cloud signing service + on-prem poll → "click Upgrade → pay → auto-unlock".
- **M3 — ship-dormant provisioning:** the ECM/Athena compose SKU profile, started/enabled on activation.

---

## 9. Open questions for gate

1. **Customer base** — mostly air-gapped (M1 offline-first) or networked (M2 sooner)?
2. **Crypto lib** — `PyJWT[crypto]` (EdDSA/RS256 JWS) vs `cryptography` (detached sig)? Both add `cryptography`.
3. **`install_id`** — generation + storage location + migration policy (what counts as "the same install")?
4. **Grace policy** — on expiry: hard stop / read-only / N-day grace?
5. **Cloud signing service** — new small service vs fold into an existing vendor backend; key custody/HSM for the private keys.
6. **Provisioning depth (M3)** — ship full Athena dormant everywhere vs pull-on-activation for the networked segment?
7. **Revocation** — do we need a CRL/`jti` deny-list, or is short `exp` + re-issue enough? (offline makes CRL hard.)

---

## 10. Relationship to the publish taskbook

Publish R3 already put ECM behind `is_enabled("plm.ecm")` (no-op now). M1 only **swaps that implementation** and adds activation/UI — **no rework** to the publish work. The early seam is exactly what makes this a flag-flip later.
