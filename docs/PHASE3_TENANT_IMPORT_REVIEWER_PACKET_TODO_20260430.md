# TODO — Phase 3 Tenant Import Reviewer Packet

Date: 2026-04-30

## Implementation

- [x] Add DB-free reviewer packet script.
- [x] Read evidence intake JSON.
- [x] Read evidence handoff JSON.
- [x] Require green intake.
- [x] Require green handoff.
- [x] Require tenant/schema/target URL consistency.
- [x] Keep `ready_for_cutover=false`.
- [x] Emit JSON and Markdown reviewer packet reports.

## Tests

- [x] Green intake and handoff build reviewer packet.
- [x] Blocked intake blocks reviewer packet.
- [x] Blocked handoff blocks reviewer packet.
- [x] Context mismatch blocks reviewer packet.
- [x] Upstream cutover-ready flag blocks reviewer packet.
- [x] CLI writes JSON and Markdown.
- [x] CLI strict mode exits 1 when blocked.
- [x] Source contract preserves reviewer-packet-only scope.

## Docs

- [x] Add development task MD.
- [x] Add verification MD.
- [x] Add runbook section.
- [x] Update parent P3.4 TODO.
- [x] Update delivery doc index.

## Explicitly Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Accept evidence.
- [ ] Build archive manifest.
- [ ] Run production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
