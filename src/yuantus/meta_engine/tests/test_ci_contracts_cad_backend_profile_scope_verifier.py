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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_cad_backend_profile_scope_verifier_is_documented_and_runnable() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_cad_backend_profile_scope.sh"
    scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    connector_doc = repo_root / "docs" / "CAD_CONNECTORS.md"
    dev_doc = repo_root / "docs" / "DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md"
    delivery_doc_index = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"

    for path in (script, scripts_index, connector_doc, dev_doc, delivery_doc_index):
        assert path.is_file(), f"Missing required path: {path}"

    syntax_cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(script)],
        text=True,
        capture_output=True,
    )
    assert syntax_cp.returncode == 0, syntax_cp.stdout + "\n" + syntax_cp.stderr

    help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_cp.returncode == 0, help_cp.stdout + "\n" + help_cp.stderr
    help_out = help_cp.stdout or ""
    for token in (
        "Usage:",
        "verify_cad_backend_profile_scope.sh",
        "BASE_URL",
        "TOKEN=<jwt>",
        "LOGIN_USERNAME=<user> PASSWORD=<password>",
        "$HOME/.config/yuantus/p2-shared-dev.env",
        "RUN_TENANT_SCOPE",
        "GET  /api/v1/cad/backend-profile",
        "GET  /api/v1/cad/capabilities",
        "DELETE or restore org override",
        "Tenant-default verification is skipped if an org override is active",
    ):
        assert token in help_out, f"help output missing token: {token}"

    scripts_index_text = _read(scripts_index)
    for token in (
        "verify_cad_backend_profile_scope.sh",
        "verifies `GET/PUT/DELETE /api/v1/cad/backend-profile` plus `GET /api/v1/cad/capabilities`",
        "restores the original org scope",
    ):
        assert token in scripts_index_text, f"DELIVERY_SCRIPTS_INDEX missing token: {token}"

    connector_doc_text = _read(connector_doc)
    for token in (
        "/api/v1/cad/backend-profile",
        "verify_cad_backend_profile_scope.sh",
        "safely restores the original org scope",
        "LOGIN_USERNAME=admin PASSWORD=admin",
        "skips tenant-default verification when an active org override masks the tenant-default read surface",
    ):
        assert token in connector_doc_text, f"CAD_CONNECTORS.md missing token: {token}"

    dev_doc_text = _read(dev_doc)
    for token in (
        "verify_cad_backend_profile_scope.sh",
        "bash -n scripts/verify_cad_backend_profile_scope.sh",
        "shell syntax stays valid",
        "LOGIN_USERNAME",
        "Claude Code CLI was used in non-interactive `-p` mode",
    ):
        assert token in dev_doc_text, f"dev-and-verification doc missing token: {token}"

    delivery_doc_index_text = _read(delivery_doc_index)
    assert (
        "docs/DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_VERIFIER_20260420.md"
        in delivery_doc_index_text
    ), "DELIVERY_DOC_INDEX missing CAD backend profile scope verifier doc"
