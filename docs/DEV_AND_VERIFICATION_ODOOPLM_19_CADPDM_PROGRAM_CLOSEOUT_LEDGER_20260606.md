# CAD-PDM Borrow Program — Closeout Ledger

Date: 2026-06-06
Status: **doc-only** stage-sealing record. Summarizes the OdooPLM-19 CAD-PDM borrow
program (#718–#735), its live capabilities, the route/migration baselines, explicit
non-goals, and the next-candidate slices. No code change.

## 1. What was delivered (the borrow program)

Source: `ODOOPLM_19_CADPDM_GAP_AND_BORROW_ANALYSIS_20260604.md` (#718). Each work
package was grounded by a doc-only taskbook, then implemented, each on its own
explicit per-phase opt-in.

| WP / phase | What | Taskbook | Impl | Status |
|---|---|---|---|---|
| WP1.0 | Representation decision (Part + role-tagged Files, not a Document graph) | #718 | — | CLOSED |
| WP1.1 | CAD-PDM relationship types (ASSEMBLY / REFERENCE) seeded | — | #720 | CLOSED |
| WP1.3 | 2D/3D staleness — provenance model (`source_batch_id`) + `needs_update`, checkin alignment | #722 | #725 | CLOSED |
| WP1.2 | PDM relationship traversal (`relationship-tree` tree/flat, node budget) | #726 | #728 | CLOSED |
| WP1.2 | `stale-drawings` thin scan (reuses `needs_update`, bounded reachable-set) | #726 | #729 | CLOSED |
| B2 | Assembly release **hard gate** (`bom.children_all_released`, fail-closed on dangling edge) | — | #731 | CLOSED |
| B2 | `item_release` diagnostics surfaced in `release_readiness` (advisory, pre-promote visibility) | — | #732 | CLOSED |
| B1 | Version **Superseded** signal + concurrent-revision guard | #734 | #735 | CLOSED |

**End-to-end value now live:** an assembly with an unreleased / missing-BOM child is
**hard-blocked at promote** *and* **visible earlier in `release_readiness`**; releasing
a new version auto-**Supersedes** the prior; concurrent re-revision is blocked by an
**app guard + DB partial-unique**.

## 2. Live baselines (as of this ledger)

- **Route count = 706** (`EXPECTED_TOTAL_ROUTES`; pins: metrics delta, phase4, breakage
  metrics, portfolio meta-contract). B1/B2/readiness added **no** routes; the only
  bumps in this window were WP1.2 traversal (+2 → 704), WP1.2 stale-drawings (+1 → 705),
  and the unrelated PLM-Collab #733 embed-token (+1 → 706).
- **Single Alembic head = `b1_supersede_001`** (chain: `…→ p2b_appr_tmpl_001 →
  wp13_cad_stale_001 (WP1.3) → b1_supersede_001 (B1)`). WP1.1/B2/readiness added no
  migrations.
- Key surfaces: `web/pdm_relationship_router.py` (`/pdm/items/...` traversal),
  `web/cad_consistency_router.py` (`/cad/items/.../staleness`, `/stale-drawings`),
  `services/release_validation.py` (`item_release` ruleset),
  `services/item_release_service.py` (gate + diagnostics),
  `lifecycle/service.py` (promote hard gate), `version/service.py` +
  `version/models.py` (supersede hook + open-current partial-unique).

## 3. Not in scope of this program (deliberate)

- No **Document** entity / document-graph (WP1.0 D4 — Part + role-tagged Files instead).
- No new lifecycle **state on the Item** for Superseded (B1 D1 — version-level only).
- No **part-replacement** model (`bom_obsolete_service` `superseded_by` is a separate,
  disjoint concept from version supersession).
- No version-scheme change, no ECO/revision-router rework, no Item-axis `is_current`/
  config-generation change (B1 D6/D7).
- No bounded-occurrence memoized flat traversal yet (WP1.2 D3 tracked follow-up; tree +
  flat share the node-budget guard today).

## 4. Separate lines interleaved in the same window (NOT CAD-PDM)

So the timeline is not misread later:
- **PLM Collaboration (cross-repo, provider+consumer):** #717 (P2.5 capability manifest),
  #723/#724 (P3-A BOM projection), #727 (P3-B SKU/manifest), #730 (P3-D0), #733 (P3-D1
  embed-token). Tracked separately (see the PLM-Collab memory); do not fold into CAD-PDM.
- **CAD material assistant:** #719 taskbook + #721 bind/write-back (and earlier
  #711/#713/#715) — CAD-adjacent but a distinct sub-line.

## 5. Next-candidate slices (each needs its own opt-in)

1. **A4 pack-and-go** (recommended next): package a root Part + its WP1.2 reachable set +
   role-tagged files into a portable bundle. Reuses WP1.2 flat/tree projection + WP1.3
   file-role / staleness signals. **NOTE: a pack-and-go plugin + contracts already exist**
   (`services/pack_and_go_db_resolver_contract.py`, `pack_and_go_version_lock_contract.py`,
   `tests/test_plugin_pack_and_go.py`) — A4 is *extend-existing*, not greenfield; its
   taskbook must ground in what those already do.
2. **Superseded read-surface:** a version-history filter for "active released" vs
   "historical" (`is_released and not is_superseded`). Small, no new model.
3. **A3 workstation checkout** (heavier, deferred): touches CAD desktop, lock state, real
   file streams / local paths, security boundary — likely an external-environment /
   native-signoff gate like the CAD-helper line. Sequence after A4 unless CAD-workstation
   is explicitly prioritized.
4. **WP1.2 bounded memoized flat** (perf follow-up before pack-and-go scales).

## 6. Verification posture

Implementation slices shipped green through the CI contracts + regression lists with
dual-registered tests where applicable (ci.yml + conftest no-DB allowlist); doc-only
taskbooks (WP1.0 #718, WP1.3 grounding #722, WP1.2 #726, B1 #734) shipped through the
doc-index / reference / sorting contracts. All went through adversarial advisor review
and owner review rounds. Anti-drift authorities: the 4 route-count pins,
`test_migration_table_coverage_contracts`, `test_delivery_doc_index_references`, and the
per-feature contract tests listed in §2.
