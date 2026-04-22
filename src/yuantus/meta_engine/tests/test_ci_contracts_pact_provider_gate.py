from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_ci_contracts_job_wires_pact_provider_verifier() -> None:
    repo_root = _find_repo_root(Path(__file__))
    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    assert ci_yml.is_file()

    text = _read(ci_yml)
    assert "pact-python==3.2.1" in text
    assert "pip install -r requirements.lock pytest pact-python==3.2.1" in text
    assert "Pact provider verifier (Metasheet2 -> Yuantus)" in text
    assert "src/yuantus/api/tests/test_pact_provider_yuantus_plm.py" in text


def test_ci_change_scope_covers_pact_provider_and_cad_diff_surface() -> None:
    repo_root = _find_repo_root(Path(__file__))
    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    assert ci_yml.is_file()

    text = _read(ci_yml)
    for token in (
        "contracts/pacts/*.json",
        "src/yuantus/api/tests/test_pact_provider_yuantus_plm.py",
        "src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py",
        "src/yuantus/meta_engine/web/cad_backend_profile_router.py",
        "src/yuantus/meta_engine/web/cad_connectors_router.py",
        "src/yuantus/meta_engine/web/cad_diff_router.py",
        "src/yuantus/meta_engine/web/cad_file_data_router.py",
        "src/yuantus/meta_engine/web/cad_history_router.py",
        "src/yuantus/meta_engine/web/cad_mesh_stats_router.py",
        "src/yuantus/meta_engine/web/cad_properties_router.py",
        "src/yuantus/meta_engine/web/cad_review_router.py",
        "src/yuantus/meta_engine/web/cad_router.py",
        "src/yuantus/meta_engine/web/cad_sync_template_router.py",
        "src/yuantus/web/cad_review.html",
    ):
        assert token in text, f"Expected detect_changes contract trigger token: {token}"
