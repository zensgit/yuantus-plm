from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
ADMIN_ROUTER = ROOT / "src/yuantus/api/routers/admin.py"
AUTH_DEPENDENCY = ROOT / "src/yuantus/api/dependencies/auth.py"
ADMIN_AUTH_DEPENDENCY = ROOT / "src/yuantus/api/dependencies/admin_auth.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_ACCESS_GUARD_TAXONOMY_CLOSEOUT_20260512.md"
)

ACCESS_GUARD_HELPERS = {
    AUTH_DEPENDENCY: {
        "require_admin_user": ("Admin role required",),
        "require_admin_permission": ("Admin permission required",),
        "require_admin_access": ("Admin required",),
    },
    ADMIN_AUTH_DEPENDENCY: {
        "require_superuser": ("Superuser required",),
        "require_platform_admin": (
            "Platform admin disabled",
            "Platform admin required",
        ),
        "require_org_admin": ("Org admin required",),
    },
}

FORBIDDEN_WEB_HELPERS = {"_ensure_admin", "_ensure_superuser"}


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


def _access_guard_details() -> set[str]:
    return {
        detail
        for helper_details in ACCESS_GUARD_HELPERS.values()
        for details in helper_details.values()
        for detail in details
    }


def test_meta_engine_web_has_no_local_admin_or_superuser_guard_helpers() -> None:
    offenders: list[str] = []
    for path in _web_runtime_files():
        local_defs = _local_defs(path)
        for helper_name in FORBIDDEN_WEB_HELPERS:
            if helper_name in local_defs:
                offenders.append(f"{path.relative_to(ROOT)}: {helper_name}")

    assert offenders == []


def test_meta_engine_web_no_longer_owns_access_guard_failure_literals() -> None:
    offenders: list[str] = []
    for path in _web_runtime_files():
        source = _source(path)
        for detail in _access_guard_details():
            if detail in source:
                offenders.append(f"{path.relative_to(ROOT)}: {detail}")

    assert offenders == []


def test_admin_router_no_longer_owns_admin_auth_guard_failure_literals() -> None:
    source = _source(ADMIN_ROUTER)
    offenders = [
        detail
        for detail in _access_guard_details()
        if detail in source
    ]

    assert offenders == []


def test_access_guard_detail_taxonomy_is_owned_by_shared_dependencies() -> None:
    for path, helper_details in ACCESS_GUARD_HELPERS.items():
        for helper_name, details in helper_details.items():
            helper_source = _function_source(path, helper_name)

            assert "HTTPException" in helper_source
            for detail in details:
                assert f'detail="{detail}"' in helper_source


def test_admin_role_guards_still_share_the_same_role_predicate() -> None:
    for helper_name in (
        "require_admin_user",
        "require_admin_permission",
        "require_admin_access",
    ):
        helper_source = _function_source(AUTH_DEPENDENCY, helper_name)

        assert "user_has_admin_role(user)" in helper_source


def test_access_guard_taxonomy_closeout_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/"
        "test_access_guard_taxonomy_closeout_contracts.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
