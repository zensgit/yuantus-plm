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
    assert "Post-merge main CI run 28082459739 passed" in text
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
