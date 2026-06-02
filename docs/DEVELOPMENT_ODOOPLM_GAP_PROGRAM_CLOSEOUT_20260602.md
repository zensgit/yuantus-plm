# OdooPLM Gap Program Closeout

Date: 2026-06-02

Scope: **doc-only program closeout.** It marks the **code-closable** OdooPLM
parity gaps complete and supersedes
`DEVELOPMENT_ODOOPLM_GAP_LEDGER_REFRESH_20260530.md` (#683) for current-state
reading. It authorizes no implementation, reuses no Odoo/OdooPLM code, and does
not rewrite the original 2026-05-25 grounded comparison (that remains the
historical evidence snapshot).

## 1. Why this closeout exists

The #683 ledger refresh (2026-05-30) recorded the state through the G3 explode
implementation (#682). Two follow-ups have since landed on `main`:

- **G3 BOM-derived auto-layout R1** — taskbook #684, implementation #685.
- **G4 category/property numbering token R1** — taskbook #686, implementation
  #687.

With those, every gap the 2026-05-25 comparison flagged as **closable by code**
is now implemented. This closeout records that end-state and frames the residual
as explicit, non-code or product-priority decisions — so the program is not
re-litigated from a stale ledger.

## 2. Final gap ledger (current `main`)

| Gap | Current state on `main` | Residual (non-code or opt-in) |
|---|---|---|
| **G1** CAD helper last mile | **Software-side closed** — helper checkout/undo/status/checkin/bom-import + six LISP commands + multipart upload (`...LAST_MILE_CLOSEOUT_20260527.md`, #662). | Native-CAD operational signoff = **hardware/operator evidence** (externally-gated); productized installer/command packaging separate. |
| **G2** PLM→ERP publication | **Functional publication spine closed** — R1 readiness API, R2 outbox/routes/worker, R3 generic HTTP connector, R4 read-only export (#663–#676). | A **named vendor ERP adapter** only when a concrete target exists (behind the registry seam). |
| **G3** 3D visual explode | **Implemented (thin server surface).** Validated explode config in `meta_3d_overlays.properties["explode"]` (#681/#682) **plus BOM-derived auto-layout R1** — explicit `part_refs` binding only, no geometry, fail-closed on ambiguity (#684/#685). | Multiple named-preset table only on a **grounded need**; geometry/rendering stay **client-side** (out of repo scope). |
| **G4** numbering vocabulary | **Complete.** Literal + UTC date + trailing `{seq}` (#679/#680) **plus the category/property `{prop}` token** — config-declared value→code map, fail-closed (#686/#687). | None outstanding in this line. |
| **G5** spare parts | **Implemented.** `ItemType(is_relationship=True)` precedent, no bespoke table, no migration (#677/#678). | Optional future tightening (release guards / MBOM-aware explode) only with a grounded need. |
| **G6** production installs / scale | **Open, non-code.** Code completeness is orthogonal to deployment evidence. | Pilot deployments, reference customers, live-scale validation. |
| minor: finishing/treatment, `plm_project` | **Open, lower priority.** No slice authorized. | Start with a grounding taskbook **only if product priority rises**. |

## 3. Program status

**The code-closable OdooPLM parity gaps (G2, G3, G4, G5) are CLOSED on `main`;
G1 is software-side closed.** What remains is, by category:

- **Externally-gated (not closable by code):** G1 native-CAD operational signoff,
  G6 production-scale evidence. These need operator/deployment artifacts, not
  another slice.
- **Product-priority decisions (unstarted, doc-first if taken):** finishing/
  treatment process attributes, `plm_project` integration.
- **Deferred-with-no-grounded-need:** G3 multiple-named-preset table, a G2
  vendor-specific adapter, G5 release-guard tightening — each opens only behind a
  scoped taskbook when a concrete need appears.

So the default posture is **stop here**: the parity program has shipped what code
can ship. Continuing should be a deliberate choice driven by product priority or
a concrete target, not by sequence.

## 4. How to read the ledger now

- This closeout is the **current-state** reference; the #683 refresh is
  superseded for that purpose (kept for history).
- `DEVELOPMENT_ODOOPLM_GROUNDED_COMPARISON_20260525.md` remains the source for
  original evidence and the GPL/AGPL-safe, semantics-only license posture; do not
  retroactively rewrite its 2026-05-25 module table as if later work existed then.
- Per-slice DEV/verification records (linked via `DELIVERY_DOC_INDEX.md`) are the
  authoritative detail for each gap.
- Status words stay deliberately narrow (no marketing overclaim): "software-side
  closed" ≠ native signoff complete; "functional publication spine closed" ≠ a
  certified vendor adapter; "thin server surface" ≠ client rendering.

## 5. Next-decision menu (each its own explicit opt-in)

1. **Stop / consolidate** (recommended default) — the parity program is closed;
   no further slice without a product reason.
2. **A minor-gap grounding taskbook** (finishing/treatment or `plm_project`) — only
   if product priority rises; doc-only first.
3. **G3 multiple-named-preset table** / **G2 vendor adapter** / **G5 tightening** —
   only behind a scoped taskbook when a concrete need exists.
4. **Market-validation track** — G1 native-CAD signoff and G6 pilot evidence;
   operator/deployment work, not code.

## 6. Non-Goals

No code changes; no Odoo/OdooPLM code reuse; no change to the GPL/AGPL-safe
semantic-only posture; no claim that any deferred item is authorized for
implementation.
