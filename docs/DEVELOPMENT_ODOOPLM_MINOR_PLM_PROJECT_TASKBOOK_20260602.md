# Claude Taskbook: OdooPLM Minor Gap — `plm_project` (Project Integration) Grounding + Right-Sizing

Date: 2026-06-02

Type: **Doc-only grounding + right-sizing taskbook.** It grounds the last
remaining minor OdooPLM gap (`plm_project`) against current `main` and concludes,
honestly, that there is **no code-closable minor slice** here — it is either a
major internal subsystem or an externally-gated integration. It authorizes no
implementation and recommends **deferral with explicit promotion trip-wires**.

Origin: `DEVELOPMENT_ODOOPLM_GROUNDED_COMPARISON_20260525.md` §2/§5 marks
`plm_project` ("与 Odoo 项目集成") as a **minor** gap with evidence "`project`→3
文件, 非完整集成", and the finishing/treatment taskbook (#689) §10 flagged that
this gap's boundary "更容易牵项目管理流程" (easily pulls in PM workflow). Baseline
`main = 2873432e` (after finishing/treatment R1 #690).

## 0. What this is (and the honest conclusion)

This is a **minor-gap** taskbook, and the disciplined outcome is **"defer, not
build."** Grounding (below) shows Yuantus has **no project subsystem at all** to
extend — so unlike finishing/treatment (which had real CAD profiles/mappers to
widen), there is no small, safe R1. A grounding taskbook whose honest finding is
"defer" is a legitimate, useful outcome (cf. the G3 sizing) — provided it says
**what would change the decision**, which §4 does.

## 1. Grounding Facts (verified against `main = 2873432e`)

`plm_project` = integration with **Odoo's project module** (linking PLM
items/ECOs to external project-management tasks/projects). In Yuantus:

- **No `Project` model.** No `class Project` / `__tablename__` for a project
  entity anywhere in `src/yuantus`, and **no `project_id` Column** on any model
  (a repo-wide sweep for `class Project*` / `project_id = Column` / a `project`
  table is empty).
- **No PLM-object project linkage.** No Item / baseline / ECO / version carries a
  first-class project reference, and there is **no project router / service /
  ItemType** (`grep project_id|project_key|project_ref` across
  `meta_engine/models/` + `meta_engine/web/` is empty).
- The `project` references that DO exist in the repo are **all incidental**, none
  a PLM project capability:
  - `seeder/...ProjectDemoSeeder` — a demo data seeder;
  - `parallel_tasks_service.py:5533` — `"project": {"key": project_key}` is the
    **JIRA** `project` field for issue creation
    (`jira_project_key`/`jira_issue_type`), i.e. external **ticketing**;
  - `api/routers/cad_preview.py:111` + `web/cad_preview.html:485` — a
    `project_id` **form/payload string** on the CAD-preview upload endpoint
    (opaque passthrough metadata), **not** a PLM project model or linkage.

Conclusion: the "`project`→3 文件" of the comparison is **incidental**, not a
partial project subsystem. There is nothing to widen.

## 2. Why there is no small R1 (the sizing)

Closing `plm_project` requires one of two things, neither of which is a
"minor-gap slice":

- **A native project-management subsystem** — a `Project` entity, Item/ECO↔project
  links, project lifecycle/membership, and likely tasks/milestones. That is a
  **major feature / its own program**, and it is exactly the PM-workflow creep the
  #689 taskbook warned about. It is **out of scope** for a minor gap.
- **An outbound PM-integration contract** — linking released PLM objects to an
  **external** PM tool's projects/tasks (the way odooplm integrates with Odoo's
  project, and the way G2 publishes to ERP). That needs a **concrete external PM
  target** and a contract; it is **externally-gated** until such a target exists.

## 3. Explicitly REJECTED: a "project tag/reference property" v0

A tempting "minimal slice" would be a `project` reference/tag **property** on
items (mirroring how finishing/treatment added a `finish` field). **This is
rejected**, because the mirror is false and the result is harmful:

- `Item.properties` is already free-form JSON and **already accepts an arbitrary
  `project` key**. Adding a "project tag" therefore ships **nothing the system
  cannot already store** — there is no new capability, no link semantics, no
  lifecycle.
- Worse, it would **imply** that "project integration" exists when it does not —
  the plausible-but-wrong, looks-like-a-feature outcome this program fails closed
  against. Finishing/treatment had a real anchor (existing CAD profiles/mappers, a
  live `{"finish":...}` use, a bounded vocabulary); `plm_project` has none.

So there is no honest v0 token slice. Do not manufacture one to have something to
merge.

## 4. Recommendation: DEFER — with promotion trip-wires

`plm_project` is **deferred** as not code-closable in a minor-gap form. It
promotes to actionable **only** on a concrete signal:

| Path | Promotion trip-wire (the signal) | Shape if promoted |
|---|---|---|
| **A — native PM subsystem** | A **product decision** that Yuantus should own native project management inside PLM. | A separate **grounded program plan** (like the G2 publication program plan), NOT a minor-gap slice. Scoped phases, own opt-ins. |
| **B — outbound PM integration** | A **concrete external PM target** (e.g. a specific Jira/Odoo-project/MS-Project endpoint) with a real need to link PLM objects to it. | An outbound integration contract behind a **registry seam** (mirror G2's adapter registry: a Null/no-op default, a concrete adapter only for the named target). Externally-gated. |

Until one of those signals exists, **no slice should be opened** — opening one
without a target/decision is how a minor gap balloons into an unwanted subsystem.

## 5. Ledger reconciliation (supersede the #688 row)

`DEVELOPMENT_ODOOPLM_GAP_PROGRAM_CLOSEOUT_20260602.md` (#688) listed
`plm_project` under "Product-priority decisions (unstarted)." This taskbook
**supersedes that row** to: **`plm_project` — deferred; no code-closable
minor-gap slice (no Yuantus project subsystem exists); promotes only on Path-A
product decision or a Path-B concrete external PM target.** With finishing/
treatment shipped (#690) and `plm_project` deferred here, the **OdooPLM
minor-gap line is exhausted** — the remaining OdooPLM items are all externally-
gated (G1 native signoff, G6 scale) or behind a concrete-target/product opt-in.

## 6. Non-Goals

- No code, no migration, no model/route/service.
- No project-tag property (§3, rejected).
- No native PM subsystem and no outbound PM integration here — those are the §4
  gated paths, each its own program/opt-in.
- No Odoo/OdooPLM code reuse; semantics only.

## 7. Reviewer Focus

1. §1 — is the negative grounding right (no `Project` model / `project_id` /
   router; the `project` refs are a demo seeder + a JIRA key)?
2. §2/§3 — is "no small R1, and the property-tag v0 is rejected (ships nothing,
   implies a non-existent feature)" the correct sizing?
3. §4 — are the two paths and their promotion trip-wires the right framing
   (product decision → Path A program; concrete external target → Path B registry
   seam)?
4. §5 — does the closeout-ledger supersession correctly close the minor-gap line?

## 8. Status

Doc-only grounding + right-sizing. Ready for review once this file and its
DEV/verification record are referenced in `DELIVERY_DOC_INDEX.md` and the
doc-index checks pass. There is **no implementation to opt into** here — the gap
is deferred; a future Path-A program plan or Path-B integration taskbook is a
separate, signal-driven opt-in.
