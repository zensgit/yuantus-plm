from __future__ import annotations

import json
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_native_workspace_playwright_package_scripts_and_readme_are_wired() -> None:
    repo_root = _find_repo_root(Path(__file__))

    package_json = repo_root / "package.json"
    readme = repo_root / "playwright" / "tests" / "README_plm_workspace.md"
    repo_readme = repo_root / "README.md"
    verification_doc = repo_root / "docs" / "VERIFICATION.md"

    assert package_json.is_file(), f"Missing {package_json}"
    assert readme.is_file(), f"Missing {readme}"
    assert repo_readme.is_file(), f"Missing {repo_readme}"
    assert verification_doc.is_file(), f"Missing {verification_doc}"

    package_data = json.loads(_read(package_json))
    scripts = package_data.get("scripts", {})

    expected_scripts = {
        "playwright:test:plm-workspace": (
            "playwright/tests/plm_workspace_documents_ui.spec.js",
            "playwright/tests/plm_workspace_demo_resume.spec.js",
            "playwright/tests/plm_workspace_document_handoff.spec.js",
            "playwright/tests/plm_workspace_eco_actions.spec.js",
        ),
        "playwright:test:plm-workspace:documents": (
            "playwright/tests/plm_workspace_documents_ui.spec.js",
        ),
        "playwright:test:plm-workspace:resume": (
            "playwright/tests/plm_workspace_demo_resume.spec.js",
        ),
        "playwright:test:plm-workspace:handoff": (
            "playwright/tests/plm_workspace_document_handoff.spec.js",
        ),
        "playwright:test:plm-workspace:eco-actions": (
            "playwright/tests/plm_workspace_eco_actions.spec.js",
        ),
    }

    for script_name, expected_tokens in expected_scripts.items():
        value = scripts.get(script_name)
        assert value, f"package.json missing native workspace Playwright script: {script_name}"
        for token in expected_tokens:
            assert token in value, f"{script_name} should reference {token}"

    readme_text = _read(readme)
    for token in (
        "npm run playwright:test:plm-workspace",
        "npm run playwright:test:plm-workspace:documents",
        "npm run playwright:test:plm-workspace:resume",
        "npm run playwright:test:plm-workspace:handoff",
        "npm run playwright:test:plm-workspace:eco-actions",
        "scripts/verify_playwright_plm_workspace_documents_ui.sh",
        "scripts/verify_playwright_plm_workspace_demo_resume.sh",
        "scripts/verify_playwright_plm_workspace_document_handoff.sh",
        "scripts/verify_playwright_plm_workspace_eco_actions.sh",
        "scripts/verify_playwright_plm_workspace_all.sh",
        "scripts/verify_all.sh",
        "plm_workspace_documents_ui.spec.js",
        "plm_workspace_demo_resume.spec.js",
        "plm_workspace_document_handoff.spec.js",
        "plm_workspace_eco_actions.spec.js",
        "plmWorkspaceDemo.js",
    ):
        assert token in readme_text, f"README_plm_workspace.md missing token: {token}"

    for rel in (
        "playwright/tests/plm_workspace_documents_ui.spec.js",
        "playwright/tests/plm_workspace_demo_resume.spec.js",
        "playwright/tests/plm_workspace_document_handoff.spec.js",
        "playwright/tests/plm_workspace_eco_actions.spec.js",
        "playwright/tests/helpers/plmWorkspaceDemo.js",
        "scripts/verify_playwright_plm_workspace_documents_ui.sh",
        "scripts/verify_playwright_plm_workspace_demo_resume.sh",
        "scripts/verify_playwright_plm_workspace_document_handoff.sh",
        "scripts/verify_playwright_plm_workspace_eco_actions.sh",
        "scripts/verify_playwright_plm_workspace_all.sh",
    ):
        assert (repo_root / rel).is_file(), f"Native workspace Playwright entrypoint missing file: {rel}"

    repo_readme_text = _read(repo_readme)
    for token in (
        "npm run playwright:test:plm-workspace",
        "playwright/tests/README_plm_workspace.md",
        "bash scripts/verify_playwright_plm_workspace_all.sh http://127.0.0.1:7910",
    ):
        assert token in repo_readme_text, f"README.md missing native workspace verification token: {token}"

    verification_text = _read(verification_doc)
    for token in (
        "Native PLM workspace browser regressions",
        "npm run playwright:test:plm-workspace",
        "npm run playwright:test:plm-workspace:eco-actions",
        "scripts/verify_playwright_plm_workspace_documents_ui.sh",
        "scripts/verify_playwright_plm_workspace_demo_resume.sh",
        "scripts/verify_playwright_plm_workspace_document_handoff.sh",
        "scripts/verify_playwright_plm_workspace_eco_actions.sh",
        "scripts/verify_playwright_plm_workspace_all.sh",
        "playwright/tests/README_plm_workspace.md",
    ):
        assert token in verification_text, (
            f"docs/VERIFICATION.md missing native workspace verification token: {token}"
        )
