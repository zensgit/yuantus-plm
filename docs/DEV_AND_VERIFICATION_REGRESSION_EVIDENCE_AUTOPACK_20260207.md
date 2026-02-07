# Dev & Verification Report - Regression Evidence Autopack (2026-02-07)

This delivery adds a repeatable "strict gate" runner plus a one-file markdown report generator.

Goal: enable unattended verification runs (pytest non-DB + pytest DB + Playwright) and produce evidence artifacts that can be committed or shared.

## Scope

- Add `scripts/strict_gate.sh`: strict gate runner (no report output).
- Add `scripts/strict_gate_report.sh`: strict gate runner + markdown report + log bundle.

## Usage

Run strict gate (no report file):

```bash
scripts/strict_gate.sh
```

Run strict gate with report + logs:

```bash
scripts/strict_gate_report.sh
```

Outputs:

- Report: `docs/DAILY_REPORTS/STRICT_GATE_YYYYMMDD-HHMMSS.md`
- Logs: `tmp/strict-gate/STRICT_GATE_YYYYMMDD-HHMMSS/`

Optional targeted pytest:

```bash
TARGETED_PYTEST_ARGS='src/yuantus/meta_engine/tests/test_esign_key_rotation.py -k rotate' \
  scripts/strict_gate_report.sh
```

## Notes

- The report generator keeps going even if one step fails so the report captures all failures in one place.
- Use `REPORT_PATH=...` and `OUT_DIR=...` if you want deterministic paths in CI.

