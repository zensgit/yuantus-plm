# TODO — Phase 3 Tenant Import Synthetic Drill

Date: 2026-04-29

## Implementation

- [x] Add DB-free synthetic drill script.
- [x] Generate synthetic operator evidence Markdown.
- [x] Generate synthetic external status JSON.
- [x] Generate synthetic operator notes Markdown.
- [x] Run existing redaction guard against synthetic artifacts.
- [x] Write synthetic drill JSON and Markdown reports.
- [x] Keep `real_rehearsal_evidence=false`.
- [x] Keep `ready_for_operator_evidence=false`.
- [x] Keep `ready_for_evidence_handoff=false`.
- [x] Keep `ready_for_cutover=false`.

## Tests

- [x] Clean drill writes artifacts and redaction report.
- [x] Synthetic artifacts are marked as not real evidence.
- [x] Plaintext-secret injection blocks without leaking the secret.
- [x] Markdown states the non-evidence boundary.
- [x] CLI writes JSON and Markdown.
- [x] CLI strict mode exits 1 on injected plaintext secret.
- [x] Source contract blocks DB/runtime/archive/handoff scope creep.

## Docs

- [x] Add development task MD.
- [x] Add verification MD.
- [x] Add runbook command section.
- [x] Update parent P3.4 TODO without marking real evidence complete.
- [x] Update delivery doc index.

## Explicitly Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Run row-copy against a non-production PostgreSQL target.
- [ ] Build a real archive from real operator evidence.
- [ ] Pass the real evidence handoff gate with real artifacts.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
