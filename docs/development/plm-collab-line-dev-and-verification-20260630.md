# PLM × MetaSheet Line — Development & Verification (2026-06-30)

Type: development + verification record for the PLM × MetaSheet integration line.

**Supersedes** `plm-collab-remaining-gated-development-order-and-verification-20260630.md`
(the `#924` ordering doc, written at baseline `36132cee`/`#923`): that record predates
the commercial/security hardening landed afterward (`#925`, `#926`, `#927`, `#928`, `#929`), so
its "nothing buildable left" claim is re-evaluated here against current `main` — which now includes
the `#928` audit readout — rather than reused.

This record does three things:

1. Records the buildable remainder that is **verified complete** on `main`, with commit evidence.
2. Records a **bounded, high-bar confirm pass** over the surfaces touched this cycle — whose
   purpose was to decide whether any *real, buildable-now, ungated* development item remains.
3. Orders the **remaining gated tracks** for parallel execution, each annotated with the single
   owner / ops / product / governance decision that must clear before code.

It does not convert any gated governance, infrastructure, or commercial-policy decision into code.

## 1. Baseline

- Yuantus `origin/main` at `47eec902` (`feat(plm-collab): add BOM writeback audit readout`, `#928`).
- MetaSheet2 `origin/main` includes `b71d8f097` (`#3395`, multi-`kid` embed) and `e3c2e21d5` (`#3392`, retry-key proof).

The governed BOM write-back feature is live end-to-end: provider projection + write-back +
embed-token spine on Yuantus, consumer review/write-back UI + relay on MetaSheet2.

## 2. Verified-Complete Buildable Remainder (this cycle)

Each item below is merged on `main` with CI evidence.

| Item | PR / commit | What it closed |
|---|---|---|
| Explicit edition readout on license status | Yuantus `#925` / `84538469` | Read-only `edition` derived purely from `is_entitled` (never `plan_type`, never an auth input); CLI + superuser admin readout; fail-closed `Community` default. |
| CSV formula-injection hardening across exports | Yuantus `#926` / `15096cad` | `safe_writer`/`safe_dict_writer` factories; **16** human-facing exports routed through the guard; the hand-built `bom_compare` builders rewritten to csv-quote + neutralize, closing the **comma-split bypass** (`"safe,=1+2"`) that re-opened formula injection. `cad_sync_template` deliberately excluded (machine round-trip). |
| BOM write-back read↔write ETag round-trip lock | Yuantus `#927` / `811d0571` | End-to-end test: projection `write_etag` (over HTTP/JSON) accepted as `If-Match` header → 200; stale → 412. Locks the cross-surface invariant the optimistic-concurrency loop depends on. (#917 implementation itself was completed earlier by `#922`/`804b6170`: `SELECT … FOR UPDATE` atomic CAS + projection `write_etag` exposure.) |
| BOM write-back audit readout | Yuantus `#928` / `47eec902` | Superuser-gated (`require_superuser`), read-only, **tenant-scoped** `GET /multitable/writeback-audit` over the existing `meta_bom_writeback_audit` rows (`Cache-Control: no-store`, static route ordered before the param routes, filter + pagination, invalid-datetime → 400, route-count pins updated) — operator visibility over the governed write-back; carries its own `DEV_AND_VERIFICATION_PHASE7_BOM_WRITEBACK_AUDIT_READOUT_20260630.md`. |
| ECO XLSX formula guard | Yuantus `#929` / `34165a8c` | `eco_export_service.to_xlsx` neutralizes header + row cells before openpyxl write; integration test loads the workbook back and asserts no cell has `data_type == "f"`. Closes the openpyxl sibling of the CSV vector; `eco_impact_apply_router` delegates to this guarded path. |
| Retry-key false-green test hardening | MetaSheet2 `#3392` / `e3c2e21d5` | Edit-UI key-reuse test now mocks `randomUUID` with distinct returns and asserts `randomUUID` called exactly once across a failed-submit retry — proving the key is reused, not re-minted. |
| Multi-`kid` embed public-key verification | MetaSheet2 `#3395` / `b71d8f097` | Consumer accepts a `kid → base64 Ed25519 public key` JSON map (fail-closed), removing the key-rotation flag-day; legacy single-key vars remain a fallback. No private key in MetaSheet2. |

## 3. Bounded Confirm Pass

A tight, high-bar adversarial pass ran over the three surfaces active across this cycle —
governed write-back (service + router), the read projection + embed-token spine, and the
MetaSheet2 consumer adapter + review UI. The bar for a *finding* was deliberately strict: real
(file:line evidence), buildable now **without** any owner / ops / product / governance decision,
and verifiable by a test. Refute-by-default; "clean" was a pre-accepted outcome. The pass ran
against `34165a8c` (before `#928` merged); `#928`'s audit-readout surface is verified separately by
its own CI, verification doc, and review (§2), not by this pass.

**Result: all three surfaces CLEAN — zero buildable-now, ungated findings.**

- **Write-back** — guard ladder matches the design order (entitlement 403 → permission 403 → 400
  malformed/empty/missing-`Idempotency-Key` → uniform 404 line-not-in-part → 409 lifecycle lock)
  with no 403-vs-404 existence leak; the per-tenant composite `UNIQUE (tenant_id, idempotency_key)`
  and its migration agree (no autogenerate drift); `begin_nested` audit-before-mutation atomicity
  holds (a non-`IntegrityError` audit failure rolls the mutation back); `If-Match`/412 preserves
  retry safety. *Refuted non-findings:* SQLite `FOR UPDATE` no-op (dev-only; prod is Postgres),
  pydantic 422-before-403 (no object lookup → no leak), PATCH not re-checking part type
  (unreachable in a well-formed DB).
- **Projection + embed** — entitlement-first read with no existence leak; output is a curated
  allowlist — no raw `Item.to_dict()` / permission / version-control internal fields; only the
  owner-ratified read-only technical IDs (`bom_line_id`, `part_id`, `path`) are emitted, and the
  per-line `write_etag` is itself a sha256;
  the embed mint uses `aud` = service audience + a separate exact-match `embed_origin` allowlist,
  TTL capped, fail-closed 503 on missing/malformed key, no EdDSA/HS256 alg-confusion; the §0
  read-only invariant holds — the embed token carries only the READ `feature_key` and authorizes
  nothing but the projection; the PATCH write surface is separate (distinct write SKU + session
  auth + lifecycle lock).
- **Consumer adapter** — `Idempotency-Key` reuse-on-retry vs fresh-on-new-edit is correct (keyed
  by `lineId`, retained on failure, deleted on success — pinned by spec); capability gating
  degrades safely (never 500); the multi-`kid` embed config is fail-closed (malformed map → 503,
  never a silent legacy fallback).

The pass also surfaced gated micro-decisions (recorded as context, not buildable work) — see §4.1.

## 4. Remaining Tracks — All Gated, Ordered for Parallel Execution

None of the items below is buildable without an owner / ops / product / governance decision.
They are ordered so that reversible, compatibility-improving, environment-only work can proceed
in parallel once unblocked, and so that write-semantics changes stay design-first.

| Order | Track | Gate that must clear before code | Parallel group |
|---|---|---|---|
| 1 | Ops activation — alerting | Ops sets `ALERT_WEBHOOK_URL` and runs a controlled failure to prove the webhook fires. | A (env) |
| 1 | Ops activation — owned-HTTPS V1.2 rerun | Ops provides owned HTTPS origins and runs the existing V1.2 staging instrument (incl. expiry → degrade → re-authorize). | A (env) |
| 1 | Deploy-environment gate + consumer can-i-deploy | A deploy pipeline calls PactFlow `record-deployment`; a provider-verification webhook lets MetaSheet2 PRs receive fresh Yuantus verification. | A (env) |
| 2 | Phase 7 locked-BOM ECO revision route | Owner ratifies whether released/locked-BOM edits create ECO revision intents, how apply is authorized, and how the UI distinguishes draft fast-path vs ECO path. | B (governance) |
| 2 | Date-obsolete revert | Owner ratifies revert semantics: reopen impact only / undo acknowledge / undo child-obsolete promotion / superseding correction event. | B (governance) |
| 3 | Phase 6 SSO / identity-session / bridge activation | Owner explicitly chooses bridge activation / continuous in-iframe UX as the next product line (write-back no longer triggers Phase 6). | C (product, deferred) |
| 4 | Broader commercial ops (vendor-private issuance, key custody, admin UX, B2 per-SKU seats, compatibility gates) | Commercial owner chooses deployment + support model. | D (commercial) |

Groups A–D are mutually independent and can run concurrently once their respective gates clear.
Within group A the three ops items are independent of each other. Group B's two governance
designs are independent. None of A–D depends on a code change from another group.

### 4.1 Gated micro-decisions surfaced by the confirm pass (context, not buildable work)

Reachable, but each needs a product / governance decision; none is a defect:

- **Write-back quantity口径** — the scalar guard accepts a non-numeric quantity string (e.g. a
  domain token like `AR` / `as-required`) and an explicit `null`. Whether to enforce numeric-only,
  allow domain tokens, or treat null-out as a legitimate edit is a product/governance call; no
  in-tree consumer breaks on the current permissive behavior.
- **Edit-UI affordance for a read-entitled / write-unentitled tenant** — the panel shows the editor
  and the submit returns a clear 403 (`无写回授权或权限不足。`) with no leak or integrity loss.
  Hiding the editor vs showing-with-clear-403 is a UX/product decision.
- **Single-use `jti` replay enforcement** is verifier-side (P3-D2, a separate MetaSheet2 service);
  the mint already records `jti`. **Per-instance (row-level) projection authorization** would be
  new authorization semantics. Both are governance/scope decisions, deferred by design.

## 5. Outcome

The bounded confirm pass agrees with the prior closeout: **there is no known *unimplemented*,
unowned, buildable-now development item left on this line.** The hardening landed this cycle
(`#925`/`#926`/`#927`/`#928`/`#929` on Yuantus, `#3392`/`#3395` on MetaSheet2) closed the last
commercial/security gaps buildable without owner input, and an adversarial re-check of the core
write-back / projection / embed / consumer surfaces found zero buildable-now ungated defects.

The remaining motion is **not coding** — it is the owner / ops / product / governance decisions
that unblock the gated tracks in §4. Once a gate clears, its track becomes buildable and can
proceed in parallel with the others per the grouping above. Each such track must take its **own
explicit opt-in** before code (per the per-phase discipline); this record does not authorize any
of them.

## Invariants held

- The embed iframe remains **read-only**; no write path was added to it.
- No private signing key material exists in MetaSheet2 (public keys only).
- `edition` and entitlement readouts derive only from `is_entitled`, never from `plan_type`.
- No owner / ops / product / governance gate was silently converted into code.
