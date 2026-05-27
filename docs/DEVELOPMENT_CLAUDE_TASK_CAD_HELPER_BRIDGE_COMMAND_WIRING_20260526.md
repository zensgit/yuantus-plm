# Claude Taskbook: CAD Helper Bridge — CAD-Host Command Wiring Design / Scope-Lock

Date: 2026-05-26

Type: **Doc-only taskbook (design / scope-lock).** Changes no runtime, schema,
workflow, or client/helper code. It scopes the in-CAD **commands** that would
drive the merged G1-A/B/C helper routes from inside the CAD host, and — its
primary job — **splits that work by client transport capability** and locks the
slice boundaries. Merging this taskbook does **NOT** authorize any
implementation and is **not** a command-wiring implementation taskbook.

## 1. Purpose

The helper last-mile routes are merged (G1-A lock/status, G1-B checkin, G1-C
BOM import; helper route count `15`). What does **not** yet exist is an in-CAD
**command** that drives them: today the only CAD-host command that touches the
helper is `C:YUANTUS_DIFF_PREVIEW` (→ `/diff/preview`, JSON). This memo scopes
the command-wiring work, resolves how it splits, and surfaces the decisions to
ratify before any implementation slice.

## 2. Grounded current state

- **Helper routes available to drive** (all merged, count `15`):
  - JSON: `POST /document/checkout`, `POST /document/undo-checkout`,
    `POST /document/status` (G1-A).
  - Multipart (file upload): `POST /document/checkin` (G1-B),
    `POST /document/bom-import` (G1-C).
- **In-CAD command surfaces today:**
  - **cad-desktop-helper LISP/NETLOAD channel** — the shared S10 LISP shell
    (`clients/cad-desktop-helper/Lisp/yuantus_cad_helper.lsp`) plus S9 bridge
    adapter defines **exactly one** command, `c:yuantus_diff_preview`, calling
    the bridge primitive `(yuantus-helper-call "ENDPOINT" json)`. The current
    static verifier is framed around ZWCAD/GstarCAD, while the bridge adapter's
    operational NETLOAD evidence also names AutoCAD; this channel is distinct
    from the AutoCAD material-sync plugin below.
  - **AutoCAD material-sync plugin** — `clients/autocad-material-sync`
    (`DedupPlugin.cs`) already registers **9** `[CommandMethod]` commands
    (5 `DEDUP*` + 4 `PLMMAT*`); its helper transport is
    `IMaterialSyncHelperTransport.PostJsonAsync<T>`.
  - **SolidWorks** — `clients/solidworks-material-sync` (SDK-free C# skeleton +
    gateway seams; no verified COM/add-in runtime adapter yet, per the assembly
    walker memo).
- **None of the 5 G1 routes has an in-CAD command driving it.** The routes
  exist; the CAD-host trigger does not.

## 3. The core split — transport capability (CENTERPIECE)

Both CAD-host command seams that could call the helper are **JSON-only today**:

- the LISP bridge primitive `(yuantus-helper-call endpoint json)` sends JSON
  (arity-2: endpoint + JSON body — enforced by the S10 verifier);
- the C# `IMaterialSyncHelperTransport` exposes only `PostJsonAsync<T>`.

The shared low-level `HelperTransport` already has a generic content method, but
neither of the current CAD-host command seams exposes a `multipart/form-data`
API. Therefore:

- **JSON routes** (`checkout` / `undo-checkout` / `status`) are drivable
  **today** by pure command wiring — no new transport, no file upload, no save.
- **Multipart routes** (`checkin` / `bom-import`) are **not** drivable by either
  client transport as-is. Wiring them requires a **new client-side multipart
  transport seam** first (extend the S9 LISP bridge `.dll`, and/or add a
  multipart method to the C# transport). That is a transport **addition**, not
  command wiring.

This is the same shape as G1-C deferring Path B: the heavier prerequisite gets
its **own** slice rather than being smuggled into the lighter one.

## 4. Three-slice phasing (proposed)

- **Slice A — JSON command wiring.** Drive `checkout` / `undo-checkout` /
  `status` from in-CAD commands using the **existing** JSON transports. No new
  transport, no save, no file upload. Lowest risk; the recommended next
  implementation slice.
- **Slice B — client multipart transport seam.** Its **own** taskbook + R1:
  decide and build how a client sends `multipart/form-data` to the helper
  (extend the S9 LISP bridge primitive vs. add a C# transport method vs. both).
  Whatever transports B picks, the B taskbook **must select one canonical
  multipart envelope** (field names, file part name, boundary handling) shared
  across them — no per-transport synonym divergence. This memo **names** B as
  the prerequisite for C and does **not** design it.
- **Slice C — multipart command wiring.** Drive `checkin` / `bom-import` from
  in-CAD commands. **Gated on Slice B merging.** Save responsibility (§6) and
  the byte-source decision live here, not in A.

Slice A is fully scoped below. B and C are named, not designed.

## 5. Decisions to ratify

- **D1 — phasing.** Adopt the three-slice split (A: JSON wiring now; B:
  multipart transport seam as its own taskbook; C: multipart wiring gated on B)?
  **Recommended: yes.**
- **D2 — Slice A scope / first host + the C# plugin charter question.** The
  AutoCAD `material-sync` plugin is chartered for dedup + material sync; adding
  PLM workflow commands (`CHECKOUT`/`CHECKIN`/`STATUS`) **expands** that
  charter. Choose:
  - **(a)** Slice A = **cad-desktop-helper LISP/NETLOAD only** JSON commands
    (the shared bridge channel, where deployed), with no material-sync plugin
    charter expansion and no PackageContents/installer churn. **Recommended.**
  - **(b)** Extend the existing C# material-sync plugin with workflow commands
    (expands its charter; touches PackageContents/README/guide guards — §7).
  - **(c)** Add a **new sibling plugin** per host under `clients/` dedicated to
    PLM workflow commands (cleanest separation; most up-front scaffolding).
- **D3 — save responsibility (Slice C only; does not affect A).** For
  `checkin`/`bom-import` the file must be on disk first. Choose **user-saves-
  first** (recommended; keeps S10 trivially intact and the helper's
  no-local-read guard honest — the caller uploads an already-saved file) vs.
  **host-native save of the active document** (the add-in issues a host save;
  see §6 for the S10 framing). Defer ratification until Slice C; recorded here
  so it is not rediscovered late.
- **D4 — multipart transport approach.** Deferred to the **Slice B** taskbook
  (extend S9 LISP bridge vs. C# transport vs. both). Whichever it picks, B must
  pin **one canonical multipart envelope** shared across transports (no
  synonym-field divergence between LISP and C#). Not decided here.

## 6. S10 display-only boundary

The S10 prohibition is on **DWG entity mutation**. The current LISP verifier
(`verify_lisp_shell_static.py:250`, `check_lsp_contains_no_dwg_mutation_or_entity_creation`)
forbids **specific** mutation forms (`(entmake`, `(entmod`, `(entdel`,
`(vla-put-`, and entity-creating `(command "TEXT"|"LINE"|"INSERT"|"MTEXT"|
"CIRCLE"|"_ERASE"|"_-PURGE"`), **not** every `(command …)`.

- **Slice A (JSON commands)** creates/modifies **no** entities and does **no**
  save — it is squarely inside the S10 boundary, like the existing diff-preview
  command.
- **Slice C save:** a document **save** persists existing state; it is not
  entity creation/modification. With **D3 = user-saves-first**, no client save
  call exists at all and S10 stays trivially intact. If host-native save is
  chosen instead, the Slice C taskbook must (i) restate that save ≠ entity
  mutation, (ii) keep every existing S10 mutation guard intact, and (iii) carry
  a deliverable static check that no entity-mutating form was introduced.
- **Reading the active file to upload it** is the *caller holding its own
  bytes*; it is distinct from the helper reading an arbitrary local path, which
  G1-B/G1-C explicitly forbid via their no-local-read guards. Slice C must
  preserve those helper-side guards unchanged.

## 7. Static-guard surfaces command wiring would shift (deliverable guards)

Per the standing rule — every static guard is a deliverable, not documentation
— a command-wiring implementation slice must treat the following as guards to
**update and re-assert**, enumerated here by file:line:

- **Route-count invariant (must stay `15` — command wiring adds NO helper
  route):**
  - `clients/cad-desktop-helper/verify_lisp_shell_static.py:348`
  - `clients/cad-desktop-helper/verify_bridge_static.py:167` (`check_helper_route_count_after_g1b`)
  - `clients/autocad-material-sync/verify_material_sync_static.py:234`
  - the 5 C# count tests (Helper.Tests ×3, Bridge.Tests, CADDedupPlugin.Client.Tests)
  - the G1-C DEV/verification doc.
  These are **invariants** for command wiring (assert unchanged), not shifts.
- **LISP command-count / name guards (WOULD shift if Slice A adds a LISP
  command):**
  - `verify_lisp_shell_static.py:208`
    `check_defines_exactly_one_command_yuantus_diff_preview` — asserts **exactly
    one** `(defun c:…)` **and** that it is `c:yuantus_diff_preview`. A new LISP
    command breaks both halves; the Slice A taskbook must update this guard to
    the new command set (count + allowed names) rather than delete it.
  - `verify_lisp_shell_static.py:353`
    `check_does_not_add_s11_integration_or_other_lisp_commands` — a forbidden
    command-name list **and** an exactly-one-`.lsp`-file assertion. New commands
    must be reconciled against both.
- **C# command-presence guard (WOULD shift if Slice A picks D2(b)/(c)):**
  - `verify_material_sync_static.py:135` `check_commands_registered` — asserts
    presence of the `PLMMAT*` commands across `DedupPlugin.cs` +
    `PackageContents*.xml` + README + guide. New workflow commands under that
    plugin must be registered the same way (and a new sibling plugin under
    D2(c) needs its own equivalent guard).

The Slice A implementation taskbook must restate each shifted guard as a real
verifier edit (not a prose claim), per the hard rule.

## 8. Non-Goals

This memo does NOT: authorize any command-wiring implementation; design the
client multipart transport seam (Slice B); wire `checkin`/`bom-import` (Slice
C); add or remove any helper route (count stays `15`); relax the S10 mutation
guards; pick the C# plugin-charter option (that is D2); decide the save model
(that is D3); commit per-host slice numbers.

## 9. Preconditions to enter the Slice A IMPLEMENTATION taskbook

1. D1 ratified (three-slice phasing accepted);
2. D2 ratified (Slice A scope: LISP/NETLOAD bridge channel vs C# plugin
   extension vs new plugin);
3. the exact new command name(s) and their target JSON routes pinned
   (`checkout`/`undo-checkout`/`status`);
4. the §7 guard shifts enumerated as concrete verifier edits in the Slice A
   taskbook (every shifted static guard is a deliverable);
5. the route-count `15` invariant restated as an explicit Slice A assertion
   (command wiring adds no helper route).

## 10. Reviewer Focus

1. Confirm §3: both CAD-host command seams are JSON-only today, so multipart
   routes need a transport seam **before** command wiring.
2. Ratify §5 **D1** (three-slice phasing) and **D2** (Slice A scope / C# plugin
   charter — recommended **(a)** LISP/NETLOAD bridge channel first).
3. Confirm §6: Slice A does no save/mutation; the save question is a Slice C /
   D3 concern and does not gate Slice A.
4. Confirm §7 lists every static-guard surface command wiring would shift, by
   file:line, with route count held at `15`.
5. Note D3 (save model) and D4 (multipart transport approach) are recorded but
   **deferred** to Slice C / Slice B respectively — not decided here.

## 11. Status

Ready for review once: the doc exists at the canonical path;
`docs/DELIVERY_DOC_INDEX.md` references it (sorted); doc-index / R2 / Tier-B
drift checks pass; `git diff --check` is clean. Ratifying §5 D1+D2 sets the next
CAD-host slice (Slice A — JSON command wiring), with Slice B (multipart
transport seam) and Slice C (multipart command wiring) named but not authorized.
