# Claude Taskbook: CAD Helper Bridge — Slice C Multipart Command Wiring

Date: 2026-05-27

Type: **Doc-only implementation taskbook.** It pins the in-CAD LISP commands
that drive the merged `yuantus-helper-upload` primitive, their behavior, the
file-source policy (and its Slice-C static guard required by the Slice B build
taskbook), the save model, and the static-guard shifts for the future Slice C
R1. It changes no code itself. **Merging this taskbook does NOT authorize the
Slice C R1 implementation** — that requires its own explicit opt-in.

Parents:

- `DEVELOPMENT_CLAUDE_TASK_CAD_HELPER_BRIDGE_COMMAND_WIRING_20260526.md` (#653 — the
  three-slice split; Slice C = multipart command wiring, gated on Slice B).
- `DEVELOPMENT_CLAUDE_TASK_CAD_HELPER_BRIDGE_SLICE_B_BUILD_20260527.md` (#657) and the
  merged Slice B R1 (#658, `63339656`), which shipped the
  `(yuantus-helper-upload "ENDPOINT" item-id filepath)` bridge primitive and
  required (§3 P1) a **Slice-C static guard that repo-owned LISP callers pass
  only the active document path** — this taskbook owns that deliverable.

## 1. Scope

Wire **two in-CAD LISP commands** that drive the merged multipart helper routes
through the Slice B bridge primitive `(yuantus-helper-upload "ENDPOINT" item-id
filepath)` (arity 3):

- `YUANTUS_CHECKIN` → `/document/checkin`
- `YUANTUS_BOM_IMPORT` → `/document/bom-import`

Slice C adds **no** helper route, **no** C#/bridge change (the primitive is
merged), and **no** material-sync change. Helper route count stays `15`; the
bridge two-primitive set stays `{yuantus-helper-call, yuantus-helper-upload}`.

## 2. Grounded current state

- The bridge primitive `yuantus-helper-upload` is merged (#658) and registered
  as the second `[LispFunction]` (AUTOCAD_HOST-gated). It uploads only to the
  allowlisted `/document/checkin` and `/document/bom-import`.
- The `.lsp` today defines **four** commands (`yuantus_diff_preview`,
  `yuantus_checkout`, `yuantus_undo_checkout`, `yuantus_status`) — none call
  `yuantus-helper-upload`. There is no in-CAD upload command yet.
- The arity-3 upload primitive is a different Lisp function from the arity-2
  `yuantus-helper-call`; the existing arity guard
  (`verify_lisp_shell_static.py:473`) matches only `yuantus-helper-call` and is
  untouched.

## 3. Pinned commands + mapping (to ratify)

| LISP command | Typeable | Bridge call | Helper route | item_id |
|---|---|---|---|---|
| `c:yuantus_checkin` | `YUANTUS_CHECKIN` | `(yuantus-helper-upload "/document/checkin" item-id filepath)` | `/document/checkin` | **required** |
| `c:yuantus_bom_import` | `YUANTUS_BOM_IMPORT` | `(yuantus-helper-upload "/document/bom-import" item-id filepath)` | `/document/bom-import` | **optional** (blank → auto-create root) |

After Slice C the `.lsp` defines **six** `(defun c:…)` total. Neither new name
collides with the forbidden-command list. Defined **after** the existing
commands so the `:354` first-occurrence ordering guard stays anchored in the
diff-preview block.

## 4. Command behavior spec (R1 must implement exactly)

Both commands:

1. Prompt for the PLM `item_id`. `YUANTUS_CHECKIN`: empty/cancel → one `(princ)`
   notice, **no** bridge call. `YUANTUS_BOM_IMPORT`: blank is **allowed** (passed
   through so the bridge omits the `item_id` part → helper auto-creates root).
2. Derive the file path from the active document **only**:
   `(strcat (getvar "DWGPREFIX") (getvar "DWGNAME"))`. Never prompt for a path,
   never `(getfiled …)`.
3. Apply the §6 save model (read the `DBMOD` modified-flag sysvar; per D-C-1).
4. Call `(yuantus-helper-upload "<route>" item-id filepath)` — arity 3 exactly.
5. On `nil` (bridge already wrote its sanitized error) → one `(princ)` notice;
   **stop** (no retry).
6. On a response → `(princ)` the bridge-returned helper `data` JSON string
   verbatim (same `SerializeDataPayload` contract as Slice A); do **not** extract
   business fields, write the DWG, or open a modal.
7. These commands do **NOT** call `/audit/apply-result`; no new `outcome`
   string.

No `(command …)` entity ops, no `(entmake/entmod/…)`, no `(open … "w"/"a")`, no
`(getfiled/alert/initdia)` — identical display-only S10 posture to the existing
commands, plus the save model in §6.

## 5. File-source policy + its Slice-C static guard (the #657 §3 P1 deliverable)

The Slice B build taskbook deferred enforcement to a **Slice-C static guard**:
repo-owned LISP callers must pass **only** the active document path as the upload
`filepath`. R1 must add a `verify_lisp_shell_static.py` guard that, for each
`(yuantus-helper-upload …)` call, the third argument is built from
`(getvar "DWGPREFIX")` + `(getvar "DWGNAME")` (e.g. via `strcat`) and is **not**
a prompted value (`getstring`/`getfiled`/raw user input). This bounds the
file source at the LISP layer (the bridge `IBridgeFileSource` validates; the
helper never reads a path). Together they keep the helper-side no-local-read
guard meaningful.

## 6. Save model (D-C-1 — to ratify)

`checkin`/`bom-import` upload the **on-disk** bytes at `DWGPREFIX+DWGNAME`. If the
drawing has unsaved edits, those bytes are stale.

- **D-C-1a (recommended) — user-saves-first + dirty abort.** Read the
  modified-flag sysvar (`DBMOD`); proceed only when it returns numeric `0`. If it
  returns non-zero or `nil`, `(princ)` a "save first" / "cannot confirm saved
  state" notice and **abort without uploading** (never upload stale bytes). No
  save, no mutation — S10 stays trivially clean; the sysvar read is read-only.
  Implementation detail: use a local variable name such as `dirty-flag`, not
  `dbmod`; the existing no-DWG-mutation verifier intentionally rejects the token
  `(setq dbmod` and must remain green.
- **D-C-1b — host-native save.** Issue `(command "_.QSAVE")` before upload. A
  save persists existing state (not an entity mutation), but it adds a
  `(command …)` side effect; if chosen, the R1 must explicitly allow `"_.QSAVE"`
  in the mutation guard and justify the side effect.

Recommendation: **D-C-1a** — read-only, no DWG side effect, user controls the
save. `DBMOD` is part of the AutoLISP-compatible sysvar surface and is readable
across all three hosts the bridge channel targets (AutoCAD via NETLOAD, ZWCAD,
GstarCAD), the same surface the existing `(getvar "PROGRAM")` host sniff uses.

## 7. Files Slice C R1 touches (and what it must NOT touch)

Touches **only**:

- `clients/cad-desktop-helper/Lisp/yuantus_cad_helper.lsp` — the two new commands
  (same file; no new `.lsp`).
- `clients/cad-desktop-helper/verify_lisp_shell_static.py` — the §8 guard shifts.
- a new `docs/DEV_AND_VERIFICATION_CAD_HELPER_BRIDGE_SLICE_C_MULTIPART_COMMAND_WIRING_R1_20260527.md`
  + its sorted `DELIVERY_DOC_INDEX.md` line.

Must **NOT** touch: any C#/bridge/helper code (the `yuantus-helper-upload`
primitive is merged); any helper route (count stays `15`); the bridge
two-primitive set; the material-sync plugins.

## 8. Static-guard shifts (deliverables — every guard is a deliverable)

In `verify_lisp_shell_static.py` (the line numbers below are a drafting-time
snapshot — that file is renamed/extended every slice, so the R1 must re-grep the
function names and re-verify the line numbers before editing; the function names
are the stable anchors):

- **`:212`/`:220` `SLICE_A_COMMAND_SET` / `check_defines_exactly_the_slice_a_command_set`**
  — extend the exact set to **six**: add `yuantus_checkin`, `yuantus_bom_import`
  (rename to the Slice-C command set). Keep it strict (exact set, not "≥1").
- **`:261` `check_each_command_nil_guards_the_bridge_response`** — extend
  per-command `(null response)` coverage to the six-command set.
- **NEW — upload arity guard.** Parallel to
  `check_lisp_function_call_arity_matches_s9_primitive` (`:473`, which stays
  arity-2 for `yuantus-helper-call`): assert every `(yuantus-helper-upload …)`
  call is **arity 3**. Needs an upload-specific arity extractor mirroring
  `find_helper_call_arities` (`:93`, which is `yuantus-helper-call`-specific).
- **NEW — upload endpoint-presence.** Assert `(yuantus-helper-upload "…" …)` is
  called with `/document/checkin` and `/document/bom-import` (mirror
  `find_helper_call_endpoints` `:159` for the upload primitive).
- **NEW — file-source policy guard (§5).** For each `(yuantus-helper-upload …)`,
  the `filepath` argument derives from `DWGPREFIX`+`DWGNAME` and is not a
  prompted path.
- **NEW — source header/load-time command-list guard.** Update the top-of-file
  docstring and the single load-time `(princ ...)` confirmation from four
  commands to the six-command post-state, and add a verifier assertion so stale
  "Defines four" / missing `YUANTUS_CHECKIN` / missing `YUANTUS_BOM_IMPORT`
  wording cannot drift back in.
- **NEW — Slice-C DEV-doc signoff guard**, parallel to
  `check_slice_a_dev_verification_records_deferred_signoff` (`:278`), asserting
  the new Slice-C DEV doc exists and records the deferred operational signoff.

Invariants to **re-assert unchanged**: route count `15`
(`check_helper_server_route_count_after_g1a` `:389`); the bridge two-primitive
set + `check_bridge_sources_unchanged_assumption` (`:560`, presence-only,
unaffected); the no-DWG-mutation (`:302`), `(princ)`-only/no-modal (`:329`),
no-`(open … "w")` (`:485`), no-shell-out (`:502`) guards; the call-arity-2 guard
for `yuantus-helper-call` (`:473`). In particular, keep the existing
`(setq dbmod` forbidden-token guard green by avoiding that local variable name
when reading `DBMOD`; do not weaken the mutation guard for D-C-1a.

## 9. Non-Goals

This taskbook does NOT: authorize the Slice C R1 implementation (separate
opt-in); change any C#/bridge/helper code; add/remove a helper route; add a
material-sync command; introduce a new `.lsp` file; finalize D-C-1 beyond the §6
recommendation (the R1 ratifies it).

## 10. Preconditions to enter the Slice C R1

1. §3 command names + the six-command post-state ratified;
2. §5 file-source policy + its static guard accepted as a deliverable;
3. §6 D-C-1 save model ratified (recommended D-C-1a);
4. §8 guard shifts enumerated as concrete verifier edits, route count held at
   `15`, the command set kept strict;
5. a Slice-C DEV/verification doc planned (deferred native-CAD operational
   signoff recorded; no on-host evidence on CI).

## 11. Reviewer Focus

1. Confirm §2: the upload primitive is merged; Slice C adds only the LISP
   callers.
2. Ratify §3 command names + the six-command set.
3. Confirm §5 — the `filepath` is bound to `DWGPREFIX`+`DWGNAME` with a static
   guard (the #657 §3 P1 deliverable), never a prompted path.
4. Ratify §6 D-C-1 (recommended D-C-1a user-saves-first + dirty abort) vs D-C-1b
   host-native save.
5. Confirm §8 lists the guard shifts by file:line — the command-set 4→6, the new
   upload arity-3 / endpoint / file-source guards — and holds route count `15`
   with the bridge set unchanged.

## 12. Status

Ready for review once: the doc exists at the canonical path;
`docs/DELIVERY_DOC_INDEX.md` references it (sorted); doc-index / sorting / Tier-B
drift checks pass; `git diff --check` is clean. Ratifying §3/§5/§6 sets the Slice
C R1 plan; **a separate explicit opt-in authorizes the implementation.** With
Slice C merged, the helper last-mile (G1-A lock/status, G1-B/C upload) is
fully command-wired end to end.
