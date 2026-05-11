"""Contracts for the post-P6 P3.4 external evidence handoff packet."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKET = ROOT / "docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_HANDOFF_PACKET_20260511.md"
VERIFY_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_HANDOFF_PACKET_20260511.md"
)
INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_handoff_packet_and_verification_md_are_indexed_and_ci_wired() -> None:
    index = _text(INDEX)
    ci_yml = _text(CI_YML)

    packet_path = str(PACKET.relative_to(ROOT))
    verify_path = str(VERIFY_MD.relative_to(ROOT))

    assert packet_path in index
    assert verify_path in index
    assert "test_p3_4_external_evidence_handoff_packet_contracts.py" in ci_yml
    assert packet_path in _text(VERIFY_MD)


def test_packet_keeps_phase5_and_p3_4_blocked_until_real_external_evidence() -> None:
    packet = _text(PACKET)

    for phrase in (
        "Prepared from `main=16c64f6`.",
        "Phase 5 provisioning/backup remains blocked.",
        "P3.4 remains blocked until real operator-run non-production PostgreSQL",
        "Do not start Phase 5 implementation.",
        "Do not enable `TENANCY_MODE=schema-per-tenant`.",
        "Do not ask Claude to fill missing evidence.",
    ):
        assert phrase in packet


def test_packet_pins_shortest_operator_path_and_review_boundary() -> None:
    packet = _text(PACKET)

    env_template_pos = packet.index("generate_tenant_import_rehearsal_env_template.sh")
    env_precheck_pos = packet.index("precheck_tenant_import_rehearsal_env_file.sh")
    full_closeout_pos = packet.index("run_tenant_import_rehearsal_full_closeout.sh")
    review_pos = packet.index("Review the generated evidence-intake")

    assert env_template_pos < env_precheck_pos < full_closeout_pos < review_pos
    assert "--confirm-rehearsal" in packet
    assert "--confirm-closeout" in packet
    assert "Ready for reviewer packet: true" in packet
    assert "Ready for cutover: false" in packet


def test_packet_rejects_synthetic_or_secret_bearing_cutover_artifacts() -> None:
    packet = _text(PACKET)

    for phrase in (
        "Synthetic drill output.",
        "Mock source or target DSNs.",
        "Any artifact containing plaintext PostgreSQL passwords.",
        "Any artifact that says `Ready for cutover: true`.",
        "postgresql://<user>:***@<host>/<database>",
        "Credentials must stay outside the repository.",
    ):
        assert phrase in packet

    assert "Ready for cutover: true\n" not in packet
    assert "postgresql://source-user:" not in packet
