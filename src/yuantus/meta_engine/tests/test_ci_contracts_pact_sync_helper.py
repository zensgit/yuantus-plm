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


def test_pact_sync_helper_is_documented_and_has_help() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "sync_metasheet2_pact.sh"
    scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert scripts_index.is_file(), f"Missing scripts index: {scripts_index}"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""
    for token in (
        "Usage:",
        "sync_metasheet2_pact.sh",
        "--check",
        "--verify-provider",
        "METASHEET2_ROOT",
        "PYTEST_BIN",
        "PROVIDER_TEST",
        "packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json",
        "contracts/pacts/metasheet2-yuantus-plm.json",
    ):
        assert token in out, f"help output missing token: {token}"

    script_text = script.read_text(encoding="utf-8", errors="replace")
    for token in (
        'SOURCE_RELATIVE_PATH="packages/core-backend/tests/contract/pacts/metasheet2-yuantus-plm.json"',
        'TARGET_RELATIVE_PATH="contracts/pacts/metasheet2-yuantus-plm.json"',
        'PROVIDER_TEST="${PROVIDER_TEST:-src/yuantus/api/tests/test_pact_provider_yuantus_plm.py}"',
        'cmp -s "${SOURCE_PATH}" "${TARGET_PATH}"',
        'cp "${SOURCE_PATH}" "${TARGET_PATH}"',
        '"${PYTEST_BIN}" -q "${PROVIDER_TEST}"',
    ):
        assert token in script_text, f"script missing contract token: {token}"

    index_text = scripts_index.read_text(encoding="utf-8", errors="replace")
    assert "sync_metasheet2_pact.sh" in index_text, (
        "docs/DELIVERY_SCRIPTS_INDEX_20260202.md must include the pact sync helper"
    )
