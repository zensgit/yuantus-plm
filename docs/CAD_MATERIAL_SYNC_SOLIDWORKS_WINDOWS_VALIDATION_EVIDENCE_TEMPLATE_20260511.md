# CAD Material Sync SolidWorks Windows Validation Evidence Template

Status: **template only; not validation evidence**

Use this template after running the CAD Material Sync SolidWorks client on a
real Windows machine with SolidWorks installed. Do not mark SolidWorks field
reading, local confirmation UI, COM write-back, or Windows runtime acceptance
complete until this template is filled with real operator output and reviewed.

## 1. Environment

```text
Operator:
Review date:
Windows version:
SolidWorks primary version:
SolidWorks service pack:
Yuantus base URL:
Yuantus commit:
Test SolidWorks document description:
```

Required primary baseline:

- SolidWorks must be a real installed desktop client, not a mock fixture.
- The test document must be a sanitized `.sldprt` or `.sldasm` copy.

Optional regression baseline:

- SolidWorks regression version:
- SolidWorks regression service pack:

## 2. Build Evidence

```text
Build command:
Build result:
Compiled add-in DLL path:
Add-in manifest or registration path:
```

Acceptance requirements:

- The add-in builds against the SolidWorks interop assemblies used on the
  Windows validation machine.
- No generated binary is committed to the repository.
- Build logs do not contain plaintext credentials or production drawing names.

## 3. SolidWorks Load Evidence

```text
Load method: add-in manager | registry | manual debug load
Loaded add-in path:
SolidWorks add-in load result:
SolidWorks add-in log path:
```

Acceptance requirements:

- SolidWorks loads the add-in without COM registration or managed assembly
  errors.
- The material sync command/menu entry is visible after load.

## 4. Command And UI Smoke Evidence

Record each command or UI result:

```text
Profile fetch result:
Property read command result:
Diff preview UI result:
Confirm write command result:
Cancel path result:
```

Acceptance requirements:

- Profile fetch reaches the configured Yuantus endpoint.
- Property read command returns SolidWorks custom property and cut-list/table
  fields.
- Diff preview UI renders the server write package before any write-back.
- Cancel path does not modify the SolidWorks document.

## 5. Field Read Evidence

Use a sanitized test part or assembly, not a production model.

```text
SolidWorks document description:
Custom property read result:
Cut-list or table read result:
Read SW-Material@Part value:
Read SW-Specification@Part value:
Read SW-Length@Part or @CutList value:
Read SW-Width@Part or @CutList value:
Read SW-Thickness@Part value:
```

Acceptance requirements:

- Reads come from a real SolidWorks document.
- Field names match the SolidWorks `SW-*@Part` or `SW-*@CutList` boundary used
  by the SDK-free fixtures.
- Mock JSON fixtures are not accepted as field-read evidence.

## 6. Write-Back Evidence

```text
Before SW-Material@Part value:
Before SW-Specification@Part value:
Diff preview screenshot path:
Write package JSON path:
User action: confirm | cancel
After SW-Material@Part value:
After SW-Specification@Part value:
Save/reopen result:
Yuantus dry-run log path:
Yuantus real-write log path:
```

Acceptance requirements:

- Diff preview is shown before write-back.
- Confirm path writes only confirmed `SW-*@Part` fields.
- Saved SolidWorks document reopens with the updated material fields still
  present.
- The write package JSON must not include AutoCAD Chinese primary fields such
  as `材料`, `规格`, `长`, `宽`, or `厚`.

## 7. Optional Regression Evidence

This section is optional for initial SolidWorks acceptance but required before
marking a separate higher-version regression item complete.

```text
SolidWorks regression installed: yes | no
SolidWorks regression version:
SolidWorks regression service pack:
SolidWorks regression build result:
SolidWorks regression load result:
SolidWorks regression field read result:
SolidWorks regression write-back result:
```

## 8. Reviewer Decision

```text
SolidWorks field read complete: no
SolidWorks local confirmation UI complete: no
Real SolidWorks write-back validated: no
Windows SolidWorks runtime accepted: no
SolidWorks regression complete: no
Reviewer:
Decision date:
Decision: pending
Reason:
```

Before real evidence is attached and reviewed, every acceptance field above
must remain `no` and the decision must remain `pending`. A future evidence
review may change these values only after the real Windows artifacts are
attached.

## 9. Rejection Rules

Reject the evidence if any item below is true:

- SolidWorks version or service pack is missing.
- The add-in did not build against real SolidWorks interop assemblies.
- The add-in did not load in SolidWorks.
- Property read evidence uses a mock fixture or synthetic output.
- Diff preview UI was not shown before write-back.
- The cancel path was not tested.
- The saved SolidWorks document was not reopened to confirm persistence.
- Any plaintext token, password, or production customer drawing content appears
  in the evidence.
- The template is submitted with placeholder values.

## 10. Local Pre-Review Check

After filling this template with real Windows output, run the local shape
validator before reviewer sign-off:

```bash
python3 scripts/validate_cad_material_solidworks_windows_evidence.py \
  docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md
```

For automation, add `--json` to emit a redaction-safe machine-readable result
that lists field-level failures without echoing evidence values.

The validator does not run SolidWorks and does not create validation evidence.
It only checks that this markdown contains the required fields, keeps secrets
out of the record, and does not accept placeholder, mock, or synthetic
evidence.

## 11. Current Repository State

As of `main=14d89e3`:

- SDK-free SolidWorks field extraction fixture and contract are merged.
- SDK-free SolidWorks diff-confirmation fixture and contract are merged.
- Real SolidWorks Add-in/COM field reading evidence is not recorded.
- Real SolidWorks local confirmation UI and write-back evidence is not recorded.
