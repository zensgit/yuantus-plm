from __future__ import annotations

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


def test_native_workspace_bundle_scope_files_exist() -> None:
    repo_root = _find_repo_root(Path(__file__))

    required = (
        "src/yuantus/web/plm_workspace.html",
        "src/yuantus/api/tests/test_plm_workspace_router.py",
        "playwright/tests/README_plm_workspace.md",
        "playwright/tests/helpers/plmWorkspaceDemo.js",
        "playwright/tests/plm_workspace_documents_ui.spec.js",
        "playwright/tests/plm_workspace_demo_resume.spec.js",
        "playwright/tests/plm_workspace_document_handoff.spec.js",
        "scripts/verify_playwright_plm_workspace_all.sh",
        "scripts/verify_playwright_plm_workspace_documents_ui.sh",
        "scripts/verify_playwright_plm_workspace_demo_resume.sh",
        "scripts/verify_playwright_plm_workspace_document_handoff.sh",
        "src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_aggregate_wrapper.py",
        "src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_playwright_entrypoints.py",
        "src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_ui_playwright_workspace_smokes.py",
        "src/yuantus/meta_engine/tests/test_delivery_scripts_index_native_workspace_playwright_contracts.py",
    )

    missing = [rel for rel in required if not (repo_root / rel).is_file()]
    assert not missing, (
        "Native workspace bundle scope is incomplete; expected files missing:\n"
        + "\n".join(f"- {rel}" for rel in missing)
    )
