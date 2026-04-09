# Benchmark Child Checklist Template

## Purpose

Copy this template into the next domain-specific `Cxx` design or verification
doc before implementation starts.

Use it to force one explicit benchmark choice, one bounded capability scope, and
one verification shape for the increment.

## Header

- Increment ID:
- Domain:
- Primary benchmark:
- Secondary references:
- Owning branch:
- Intended staging branch:

## Benchmark Decision

- [ ] one primary benchmark target is chosen
- [ ] the benchmark target is one of:
  - `Aras Innovator`
  - `Odoo18 PLM`
  - `DocDoku`
- [ ] any secondary references are listed explicitly and are not being treated
      as the main target

## Scope Guard

- [ ] the increment stays inside the benchmark class already assigned to the domain
- [ ] the increment does not silently switch benchmark language mid-design
- [ ] the increment does not reopen unrelated orchestration or write paths unless
      that is explicitly part of the benchmark decision

## Existing Evidence To Reuse

- plan docs:
- design docs:
- verification docs:
- implementation paths:
- prior staging regression evidence:

## Capability Checks

- [ ] required existing capability surface has been identified
- [ ] new capability extends that surface rather than bypassing it
- [ ] export/read-model/report coverage is defined where applicable
- [ ] endpoint/service/test ownership is clear before implementation begins

## Domain-Specific Acceptance Checks

### For `box`
- [ ] lifecycle, custody, occupancy, aging, and export semantics remain aligned
      with the current Odoo18-style stock/location visibility model

### For `document_sync`
- [ ] freshness, replay, lineage, lag, skew, and export semantics remain aligned
      with the current Odoo18-style sync visibility model

### For `cutted_parts`
- [ ] quote, benchmark, threshold, alert, cadence, and saturation semantics
      remain aligned with the current Odoo18-style manufacturing visibility model

### For `file-cad`
- [ ] preview, geometry, metadata, connector, and conversion semantics remain
      aligned with the current DocDoku-style integration model

## Verification Plan

- [ ] targeted domain tests listed
- [ ] broader staging regression listed
- [ ] `git diff --check` listed
- [ ] any missing legacy verification script is called out explicitly rather than
      silently skipped

## Exit Criteria

- [ ] benchmark choice is still correct after implementation
- [ ] changed files match the stated domain scope
- [ ] verification evidence is recorded in the increment verification doc
- [ ] staging branch state is ready for review or the next merge-prep step
