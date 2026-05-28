# DEV & Verification: CAD Helper Bridge Last-Mile — Program Closeout

Date: 2026-05-27

Records the completion (software side) of the CAD helper bridge **last-mile**
program and its verification state, and the decision to **pause** at this point.
The program originated from the OdooPLM grounded comparison (#643), whose #1 gap
was the CAD client last-mile. That gap is now closed end to end on `main`
(baseline `b0a39829`): backend routes, in-CAD command wiring, the client
multipart transport seam, and the operator signoff runbook are all merged.

This is a **doc-only** closeout record. The only remaining item — native-CAD
operational signoff on real hosts — is hardware/operator-gated and is **not**
claimed here (see §4).

## 1. Program ledger (merged to main)

| PR | Commit | Kind | Content |
|---|---|---|---|
| #643 | `7db5b1de` | doc | OdooPLM grounded comparison & gap analysis (origin) |
| #644 | `c809c25b` | doc | G1 last-mile design / scope-lock |
| #645 | `f5944c4f` | doc | G1-A document lock routes taskbook |
| #646 | `2c471aac` | feat | G1-A checkout / undo-checkout / status routes R1 (route count 10→13) |
| #647 | `e4399da4` | doc | G1-B checkin multipart taskbook |
| #648 | `6ee4e66b` | feat | G1-B `/document/checkin` multipart R1 (13→14) |
| #649 | `f10cc0c2` | doc | G1-C BOM path decision memo (Path A) |
| #650 | `debdf286` | doc | G1-C BOM import taskbook |
| #651 | `47068264` | feat | G1-C `/document/bom-import` (Path A) R1 (14→15) |
| #652 | `b58a753f` | doc | per-host assembly walker scope-lock (walker deferred, Path-B-gated) |
| #653 | `bda0992a` | doc | CAD-host command wiring design / scope-lock (three-slice split) |
| #654 | `832f1231` | doc | Slice A JSON command wiring taskbook |
| #655 | `ea83b04f` | feat | Slice A R1 — `YUANTUS_CHECKOUT` / `_UNDO_CHECKOUT` / `_STATUS` |
| #656 | `6b49182a` | doc | Slice B multipart transport seam design + canonical envelope pin |
| #657 | `a5b727c5` | doc | Slice B build taskbook (`yuantus-helper-upload` C# seam) |
| #658 | `63339656` | feat | Slice B R1 — bridge multipart upload primitive |
| #659 | `758ecf15` | doc | Slice C multipart command wiring taskbook |
| #660 | `befd519d` | feat | Slice C R1 — `YUANTUS_CHECKIN` / `YUANTUS_BOM_IMPORT` |
| #661 | `b0a39829` | doc | native-CAD operational signoff runbook |

## 2. What is on main

- **Backend / helper routes** (count `15`): `/document/checkout`,
  `/document/undo-checkout`, `/document/status` (G1-A), `/document/checkin`
  (G1-B, multipart), `/document/bom-import` (G1-C, multipart, Path A reusing the
  async `/cad/import` + `cad_bom` extraction).
- **In-CAD commands** (`yuantus_cad_helper.lsp`, six total): `YUANTUS_DIFF_PREVIEW`
  (S10), `YUANTUS_CHECKOUT` / `YUANTUS_UNDO_CHECKOUT` / `YUANTUS_STATUS` (Slice A,
  JSON via `yuantus-helper-call`), `YUANTUS_CHECKIN` / `YUANTUS_BOM_IMPORT`
  (Slice C, multipart via `yuantus-helper-upload`).
- **Client multipart transport seam** (Slice B): bridge `[LispFunction]`
  `yuantus-helper-upload` + `BridgeCallService.Upload` + `SharedBridgeTransport`
  multipart over the canonical envelope (`file` part + optional `item_id`),
  reusing Shared `HelperTransport.PostContentAsync`; fixed-token file-source with
  no path leak; ASCII-safe filename sanitizer; upload-endpoint allowlist
  (`/document/checkin` + `/document/bom-import` only — not a generic tunnel).
- **Discipline invariants held throughout**: no code reuse from the
  LGPL/AGPL-mixed odooplm (contract-level alignment only); display-only S10
  boundary (no DWG entity mutation); helper never reads a local path (the bridge
  holds the caller's own bytes); fail-closed save model (`DBMOD = 0`); every §6
  static guard shipped as a real verifier check.

## 3. Verification state (green on main)

- CI gates: `contracts` + `detect_changes` were green at each merge; Windows
  `dotnet build/test` was green for the C#-touching implementation PRs and
  scope-skipped for doc-only PRs; `mergeStateStatus = CLEAN` at each merge.
- Static verifiers: `verify_lisp_shell_static.py` **28**,
  `verify_bridge_static.py` **13** (two-primitive set + upload allowlist),
  `verify_material_sync_static.py` pass.
- Helper route count pinned at **15** across the three Python verifiers + the
  C# count tests + DEV docs.
- doc-contract suite (delivery-doc-index references + sorting, runbook-index
  completeness, DEV/verification index completeness + sorting) — pass.
- `git diff --check` clean.

C# (`net46` bridge + Shared) was not buildable locally; build/xUnit ran on
Windows CI (the standing "C# build/xUnit deferred to Windows CI" gate) and is
green.

## 4. Remaining item — native-CAD operational signoff (deferred)

The only open item is executing the §-rows of
`CAD_HELPER_BRIDGE_NATIVE_CAD_OPERATIONAL_SIGNOFF_RUNBOOK_20260527.md` (#661) on
real **AutoCAD 2018/2024 / ZWCAD 2025 / GstarCAD 2025** hosts: `NETLOAD` the
bridge, load the `.lsp`, run the six commands against a live helper + PLM, and
archive operator evidence. CI cannot cover this (no CAD host on the runner). A
**separate evidence/signoff PR** asserts "native-CAD signoff completed" once the
runbook's per-host summary is filled and artifacts archived. Nothing in this
track is further implementation or scope/spec work — the remaining work is
hardware/operator execution plus a later evidence PR that records the artifacts.

## 5. Status — paused at a clean completion point

The last-mile is complete on the software side; there is no pending
implementation or specification work whose continuation would add value. The
program is **paused** here until either operator evidence is collected or a new
program starts. When work resumes, the highest-value next thread is the OdooPLM
comparison's other major gap — **PLM→ERP surface** — which should open as a
deliberate new program beginning with a read-only grounding pass of the current
PLM→ERP surface (to avoid the "over-claim then verify" lesson from #643), not on
momentum.
