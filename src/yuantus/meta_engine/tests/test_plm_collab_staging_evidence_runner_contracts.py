from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "dev" / "collect_staging_evidence.sh"


def _minimal_env(out: Path, *, strict: bool = False) -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", ""),
        "PATH": os.environ.get("PATH", ""),
        "STAGING_EVIDENCE_OUT": str(out),
        "STAGING_EVIDENCE_STRICT": "1" if strict else "0",
    }


def _write_fake_yuantus(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
args="$*"
case "$args" in
  *"license status"*)
    echo 'license status for tenant: acme'
    echo 'features (sellable SKUs):'
    echo '  bom_multitable           ENTITLED'
    echo 'debug Authorization: Bearer status-secret-token-abcdefghijklmnopqrstuvwxyz'
    echo 'debug DATABASE_URL=postgresql://status_user:status_pass@db.example/plm'
    echo 'debug {"license_data":"raw-license-status-payload"}'
    ;;
  *"seats-set.json"*)
    echo 'seat cap projected: TenantQuota.max_users=2'
    ;;
  *"seats-clear.json"*)
    echo 'seat cap cleared: TenantQuota.max_users -> unlimited (NULL)'
    ;;
  *)
    echo 'activated tenant=acme app=plm.bom_multitable expires=None'
    ;;
esac
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_staging_evidence_runner_dry_run_records_not_run_sections(tmp_path: Path) -> None:
    out = tmp_path / "evidence.md"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=_minimal_env(out),
        text=True,
        capture_output=True,
        check=True,
    )

    assert f"staging evidence written: {out}" in result.stdout
    text = out.read_text(encoding="utf-8")
    assert "## 2. PactFlow Broker Real-Run" in text
    assert "Yuantus #861 squash merged at a352baa9" in text
    assert "Computer says yes" not in text
    assert "License import/status -- set SIGNED_LICENSE_PATH" in text
    assert "Capability manifest and BOM context -- set YUANTUS_BASE_URL" in text
    assert "Seats set/enforce -- set SEATS_SET_LICENSE_PATH" in text
    assert "Seats clear -- set SEATS_CLEAR_LICENSE_PATH" in text
    assert "- [x] Not trialable; blocking reason: required staging evidence is missing or failing." in text
    assert (
        "- [ ] Full post-broker baseline: section 2 PactFlow broker real-run is PASS, "
        "but staging sections are incomplete."
    ) in text


def test_staging_evidence_runner_strict_refuses_incomplete_evidence(tmp_path: Path) -> None:
    out = tmp_path / "evidence.md"

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=_minimal_env(out, strict=True),
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert out.exists()
    assert "staging evidence incomplete" in result.stderr


def test_staging_evidence_runner_redacts_captured_secret_shapes(tmp_path: Path) -> None:
    out = tmp_path / "evidence.md"
    fake_yuantus = tmp_path / "fake-yuantus"
    _write_fake_yuantus(fake_yuantus)

    env = _minimal_env(out)
    env.update(
        {
            "YUANTUS_CMD": str(fake_yuantus),
            "SIGNED_LICENSE_PATH": str(tmp_path / "license.json"),
            "PILOT_TENANT": "acme",
            "SEATS_SET_LICENSE_PATH": str(tmp_path / "seats-set.json"),
            "SEAT_CAP_EXPECTED": "2",
            "SEATS_ENFORCE_CHECK_CMD": (
                "printf '%s\\n' "
                "'blocked Authorization: Bearer enforce-secret-token-abcdefghijklmnopqrstuvwxyz' "
                "'postgres://enforce_user:enforce_pass@db.example/plm' "
                "'{\"license_data\":\"raw-enforce-payload\"}'"
            ),
            "SEATS_CLEAR_LICENSE_PATH": str(tmp_path / "seats-clear.json"),
            "SEATS_CLEAR_CHECK_CMD": (
                "printf '%s\\n' "
                "'cleared Authorization: Bearer clear-secret-token-abcdefghijklmnopqrstuvwxyz' "
                "'DATABASE_URL=mysql://clear_user:clear_pass@db.example/plm' "
                "'{\"license_data\":\"raw-clear-payload\"}'"
            ),
        }
    )

    subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    text = out.read_text(encoding="utf-8")
    assert "status-secret-token" not in text
    assert "enforce-secret-token" not in text
    assert "clear-secret-token" not in text
    assert "status_pass" not in text
    assert "enforce_pass" not in text
    assert "clear_pass" not in text
    assert "raw-license-status-payload" not in text
    assert "raw-enforce-payload" not in text
    assert "raw-clear-payload" not in text
    assert "Authorization: <redacted>" in text
    assert "<redacted-db-url>" in text
    assert "redacted_license_payload" in text
