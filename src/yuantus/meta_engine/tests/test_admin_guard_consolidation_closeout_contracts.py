from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
AUTH_DEPENDENCY = ROOT / "src/yuantus/api/dependencies/auth.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_ADMIN_GUARD_CONSOLIDATION_CLOSEOUT_20260512.md"
)

ADMIN_GUARD_HELPERS = {
    "require_admin_user": "Admin role required",
    "require_admin_permission": "Admin permission required",
    "require_admin_access": "Admin required",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _local_defs(path: Path) -> set[str]:
    tree = ast.parse(_source(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _function_source(path: Path, name: str) -> str:
    source = _source(path)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"{name} not found in {path}")


def _web_runtime_files() -> list[Path]:
    return sorted(path for path in WEB_DIR.rglob("*.py") if path.is_file())


def test_meta_engine_web_has_no_local_ensure_admin_helpers() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in _web_runtime_files()
        if "_ensure_admin" in _local_defs(path)
    ]

    assert offenders == []


def test_meta_engine_web_no_longer_owns_admin_failure_literals() -> None:
    offenders: list[str] = []
    for path in _web_runtime_files():
        source = _source(path)
        for detail in ADMIN_GUARD_HELPERS.values():
            if detail in source:
                offenders.append(f"{path.relative_to(ROOT)}: {detail}")

    assert offenders == []


def test_admin_guard_detail_taxonomy_is_owned_by_auth_dependency() -> None:
    for helper_name, detail in ADMIN_GUARD_HELPERS.items():
        helper_source = _function_source(AUTH_DEPENDENCY, helper_name)

        assert "user_has_admin_role(user)" in helper_source
        assert f'detail="{detail}"' in helper_source


def test_admin_guard_closeout_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/"
        "test_admin_guard_consolidation_closeout_contracts.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
