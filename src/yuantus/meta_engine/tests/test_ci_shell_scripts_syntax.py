from __future__ import annotations

import subprocess
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def _bash_n(script: Path) -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(script)],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_ci_and_ops_shell_scripts_are_syntax_valid() -> None:
    repo_root = _find_repo_root(Path(__file__))
    scripts_dir = repo_root / "scripts"

    # Keep this list small and focused on scripts used by CI workflows or ops runbooks.
    paths = [
        scripts_dir / "ci_change_scope_debug.sh",
        scripts_dir / "strict_gate_report.sh",
        scripts_dir / "demo_plm_closed_loop.sh",
        scripts_dir / "release_orchestration.sh",
        scripts_dir / "mt_pg_bootstrap.sh",
        scripts_dir / "verify_all.sh",
        scripts_dir / "verify_release_orchestration.sh",
        scripts_dir / "verify_esign_api.sh",
        scripts_dir / "verify_dedup_management.sh",
        scripts_dir / "verify_quota_enforcement.sh",
        scripts_dir / "verify_platform_tenant_provisioning.sh",
        scripts_dir / "verify_item_equivalents.sh",
        scripts_dir / "verify_version_file_binding.sh",
        scripts_dir / "verify_versions_e2e.sh",
        scripts_dir / "verify_where_used_e2e.sh",
        scripts_dir / "verify_effectivity_extended_e2e.sh",
        scripts_dir / "verify_bom_obsolete_e2e.sh",
        scripts_dir / "verify_bom_weight_rollup_e2e.sh",
        scripts_dir / "verify_bom_compare_e2e.sh",
        scripts_dir / "verify_bom_effectivity_e2e.sh",
        scripts_dir / "verify_bom_tree_e2e.sh",
        scripts_dir / "verify_bom_substitutes_e2e.sh",
        scripts_dir / "verify_mbom_convert_e2e.sh",
        scripts_dir / "verify_mbom_routing_e2e.sh",
        scripts_dir / "verify_routing_primary_release_e2e.sh",
        scripts_dir / "verify_routing_operations_e2e.sh",
        scripts_dir / "verify_routing_copy_e2e.sh",
        scripts_dir / "verify_baseline_e2e.sh",
        scripts_dir / "verify_baseline_filters_e2e.sh",
        scripts_dir / "verify_workcenter_e2e.sh",
        scripts_dir / "verify_cad_dedup_vision_s3.sh",
        scripts_dir / "verify_cad_dedup_relationship_s3.sh",
        scripts_dir / "verify_cad_ml_quick.sh",
        scripts_dir / "verify_cad_preview_online.sh",
        scripts_dir / "verify_run_h.sh",
    ]

    for p in paths:
        assert p.is_file(), f"Missing script: {p}"
        _bash_n(p)


def test_release_orchestration_script_has_help() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "release_orchestration.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Usage:" in (cp.stdout or "")
    assert "release_orchestration.sh plan" in (cp.stdout or "")
    assert "release_orchestration.sh execute" in (cp.stdout or "")


def test_strict_gate_report_script_has_help() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_report.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""
    assert "Usage:" in out
    assert "strict_gate_report.sh" in out
    assert "OUT_DIR" in out
    assert "REPORT_PATH" in out
