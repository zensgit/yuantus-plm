# TODO — Phase 3 Tenant Import Readiness Status

Date: 2026-04-30

## Documentation

- [x] Add P3.4 readiness status artifact.
- [x] State local toolchain is complete through reviewer packet.
- [x] State operator-run PostgreSQL rehearsal evidence is still missing.
- [x] State production cutover is not authorized.
- [x] State runtime `TENANCY_MODE=schema-per-tenant` is not enabled.
- [x] List next valid external operator actions.
- [x] Track 2026-05-05 DB-free operator safety additions.
- [x] Keep env-file precheck, command-file validator, and wrapper safety contracts scoped to local safety.
- [x] Track source/target URL env-name allowlist hardening as local safety only.
- [x] Track env-file key allowlist hardening as local safety only.
- [x] Track command-file executable-line allowlist hardening as local safety only.
- [x] Track command-file option-line allowlist hardening as local safety only.
- [x] Track command-file safe path option validation as local safety only.
- [x] Track command-file quoted metadata expansion guard as local safety only.
- [x] Add verification MD.
- [x] Update delivery doc index.

## Contracts

- [x] Keep parent P3.4 TODO real evidence item unchecked.
- [x] Assert readiness status exists.
- [x] Assert readiness status preserves cutover/runtime block.
- [x] Assert readiness status points to external operator execution.
- [x] Assert readiness status tracks local safety additions without closing the external evidence gate.
- [x] Assert URL env-name allowlist does not close the external evidence gate.
- [x] Assert env-file key allowlist does not close the external evidence gate.
- [x] Assert command-file executable-line allowlist does not close the external evidence gate.
- [x] Assert command-file option-line allowlist does not close the external evidence gate.
- [x] Assert command-file safe path option validation does not close the external evidence gate.
- [x] Assert command-file quoted metadata expansion guard does not close the external evidence gate.

## Explicitly Not Done

- [ ] Add operator-run PostgreSQL rehearsal evidence.
- [ ] Mark P3.4 rehearsal complete.
- [ ] Enable production cutover.
- [ ] Enable runtime `TENANCY_MODE=schema-per-tenant`.
