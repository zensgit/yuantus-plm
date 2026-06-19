# PLM BOM Review Add-on — V1 Acceptance Checklist

**Date:** 2026-06-19 · **For:** signing off a V1 dogfood / controlled-demo deployment.
Honest separation of **what is proven where** — in-process (runs in CI), operator (runs against a live
deploy), and deferred (later version).

## A. In-process proof (runs in CI; verified on `main` 2026-06-19)

- [x] Offline license import → entitlement mechanism — `test_license_import.py` (13 passed).
- [x] BOM context 三态 (entitled / unentitled `context:null` / existing==missing no-leak) —
      `test_bom_multitable_projection.py`.
- [x] Embed-token mint gates (entitlement, origin, fail-closed) — `test_bom_multitable_embed_token.py`.
- [x] Advisory capability manifest (advisory≠auth; `bom_multitable` supported) — `test_integration_capabilities.py`.
- [x] Entitlement kernel (fail-closed, tenant-scoped) — `test_entitlement_service.py`.
- [x] Base flag-OFF surface unchanged — `test_metasheet_bridge_flag_contracts.py` (5 passed).
- [x] Compose profile flags (`base`/`collab`/`combined`) — `test_ci_contracts_compose_sku_profiles.py`.
- [x] Dogfood signer produces a valid perpetual `plm.bom_multitable` license, self-verify PASS, and
      (proven) entitles its tenant only — `scripts/dev/sign_dogfood_license.py`.

> Combined surface run 2026-06-19: **66 passed** + signer + entitled-seed proof. (V1 feature code is on `main`.)

## B. Operator proof (run against the live combined deployment — written-not-run-in-CI)

- [ ] `scripts/dev/smoke_combined_profile.sh` — combined up, manifest reachable + `advisory:true`,
      (optional) base profile bridge route absent.
- [ ] `scripts/dev/smoke_bom_review_api.sh` — the 三态 against the live deploy.
- [ ] Real license signed + imported; `integrations/capabilities` shows `bom_multitable.entitled:true`
      for the pilot tenant only.
- [ ] **Tenant forwarding (the most likely silent failure):** `PLM_TENANT_ID=<PILOT_TENANT>` set on the
      MetaSheet backend → the workbench `/context` call returns `entitled:true` (the adapter applies
      `x-tenant-id` via `getEffectiveTenantId`/`applyTenantOrgHeaders`). If `entitled:false` despite a clean
      license import, this knob (or a per-source `options.tenantId`, REST-schema-limited) is the cause.
- [ ] `YUANTUS_AUTH_MODE=required`; single tenant; MetaSheet PLM data source configured.

## C. Constraints honored (contract/expectation language)

- [ ] Perpetual license (`expires_at=null`); no dated license issued.
- [ ] Fixed Yuantus↔MetaSheet version pair recorded for this deployment.
- [ ] No key rotation; no multi-tenant on this deployment.
- [ ] Users log into MetaSheet directly (no PLM SSO).
- [ ] No automation execution / no write-back / no in-PLM iframe presented.

## D. Deferred — NOT part of V1 (do not promise)

- In-PLM iframe host + embed-token click-through → **V1.1 pact then V1.2**.
- Hiding the `approval_automation` "升级审批自动化" entry → **V1.1** (MetaSheet owner-gated; harmless for internal dogfood).
- Modern-surface pact (manifest + BOM context) → **V1.1**.
- Vendor-private issuance / seats / grace / admin UX / multi-`kid` rotation → **V2**.
- Approval automation execution (Phase 5) · SSO (Phase 6) · controlled write-back (Phase 7).
