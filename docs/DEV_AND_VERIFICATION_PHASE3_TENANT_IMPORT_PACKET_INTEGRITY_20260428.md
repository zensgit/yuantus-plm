# DEV and Verification - Phase 3 Tenant Import Packet Integrity

Date: 2026-04-28

## 1. Goal

Strengthen the P3.4.2 implementation packet gate so it validates the full
artifact chain referenced by next-action before telling the operator that Claude
can implement the importer.

## 2. Changes

Updated `src/yuantus/scripts/tenant_import_rehearsal_implementation_packet.py`.

The packet generator now:

- imports expected schema versions from the upstream gate scripts;
- reads the six artifact files referenced by next-action;
- blocks if any artifact path is missing or does not exist;
- blocks if any artifact has the wrong schema version;
- blocks if any artifact's ready flag is not true;
- blocks if any artifact contains blockers;
- blocks if tenant ID or target schema contradicts next-action context;
- emits an `artifact_validations` array in JSON;
- renders an `Artifact Integrity` table in Markdown.

## 3. Tests

Updated `src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py`.

The tests now write realistic green upstream artifacts and cover:

- happy path across all six artifacts;
- non-final next-action;
- missing artifact path;
- missing artifact file;
- blocked artifact;
- context mismatch;
- CLI JSON/Markdown output;
- source-level no DB / no mutation guard.

## 4. Scope Controls

This PR does not implement `yuantus.scripts.tenant_import_rehearsal`.

It does not connect to source or target databases, export rows, import rows,
create schemas, run migrations, downgrade, clean up, or enable runtime
schema-per-tenant mode.

## 5. Verification

Packet-focused test:

```text
9 passed in 0.13s
```

Full focused suite:

```text
implementation-packet/next-action/source-preflight/target-preflight/plan/handoff/readiness/dry-run/doc-index: 78 passed, 1 skipped, 1 warning
```

Runbook and index contracts:

```text
5 passed
```

Compile and whitespace:

```text
py_compile: passed
git diff --check: clean
```

## 6. Next Step

The next safe implementation step is the fail-closed importer scaffold:

- add `yuantus.scripts.tenant_import_rehearsal`;
- validate `--confirm-rehearsal`;
- validate implementation packet and all upstream artifacts before any DB
  connection;
- emit blocked JSON/Markdown reports when not ready;
- still avoid real row import until the scaffold guard is proven.
