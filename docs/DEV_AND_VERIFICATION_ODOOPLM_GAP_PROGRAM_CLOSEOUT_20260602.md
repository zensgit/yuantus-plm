# DEV & Verification: OdooPLM Gap Program Closeout

Date: 2026-06-02

Records the doc-only delivery of `DEVELOPMENT_ODOOPLM_GAP_PROGRAM_CLOSEOUT_20260602.md`
— the final program closeout marking the code-closable OdooPLM parity gaps
complete and superseding the #683 ledger for current-state reading. Doc-only: no
code; authorizes no implementation. Baseline `main = d6610476` (after G4
property-token #687).

## 1. What changed

- New OdooPLM gap **program closeout**: a refreshed final ledger (G2/G3/G4/G5
  implemented; G1 software-side closed; G6 externally-gated; minor gaps =
  product-priority decisions) that supersedes the stale #683 refresh, plus a
  next-decision menu and the narrow-status-wording discipline.
- This DEV/verification record.
- Two sorted `DELIVERY_DOC_INDEX.md` entries (under `## Development &
  Verification`).

## 2. Grounding (against `main = d6610476`)

The #683 ledger recorded state through G3 explode (#682); since then **G3
BOM-derived auto-layout** (#684 taskbook / #685 impl) and **G4 category/property
token** (#686 taskbook / #687 impl) landed — verified present on `main`
(`_render_prop_token` + the explode `auto-layout` route; their DEV records in the
index). The closeout's per-gap PR references (#662, #663–#676, #677/#678,
#679/#680, #681/#682, #684/#685, #686/#687) match the merged history.

## 3. Locked decisions (summary)

The code-closable G-series (G2/G3/G4/G5) is **closed**; G1 software-side closed.
Residual is externally-gated (G1 native signoff, G6 scale — non-code) or
product-priority (finishing/treatment, `plm_project`) or deferred-with-no-grounded-
need (G3 multiple-preset table, G2 vendor adapter, G5 tightening). Default posture:
**stop**; continue only on a deliberate product/target-driven opt-in. No code, no
Odoo reuse, GPL/AGPL-safe posture unchanged.

## 4. Verification (this doc-only PR)

- doc-contract pytests — delivery-doc-index references; `## Development &
  Verification` sorting + completeness; doc-index sorting — pass.
- `verify_lisp_shell_static.py` 28, `verify_bridge_static.py` 13,
  `verify_material_sync_static.py` — pass (unchanged; no client/helper change).
- `git diff --check` clean.

## 5. Status

Doc-only program closeout. The OdooPLM parity program is closed for code-closable
gaps; the next action is a deliberate, separately-opted decision (or stop).
