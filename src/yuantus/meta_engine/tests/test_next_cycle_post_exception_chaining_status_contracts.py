"""Contracts for the post-exception-chaining next-cycle status refresh.

These tests keep the planning docs aligned with the latest local debt
closeout while preserving the Phase 5 external-evidence gate.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md"
DEV_VERIFICATION_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_NEXT_CYCLE_POST_EXCEPTION_CHAINING_STATUS_REFRESH_20260514.md"
)
RESIDUAL_CLOSEOUT_CONTRACT = (
    ROOT / "src/yuantus/meta_engine/tests/test_residual_router_exception_chaining_closeout.py"
)
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
API_DIR = ROOT / "src/yuantus/api"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"
EXCEPTION_NAMES = {"e", "exc", "err", "ex", "error", "exception"}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat_markdown(text: str) -> str:
    return " ".join(line.removeprefix("> ").strip() for line in text.splitlines())


def _contains_exception_reference(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id in EXCEPTION_NAMES
        for child in ast.walk(node)
    )


def _is_stringified_exception_detail(node: ast.AST) -> bool:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id in {"str", "repr"} and any(
            _contains_exception_reference(arg) for arg in node.args
        )
    if isinstance(node, ast.JoinedStr):
        return any(
            isinstance(value, ast.FormattedValue)
            and _contains_exception_reference(value.value)
            for value in node.values
        )
    return False


def _is_http_exception_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id == "HTTPException"
    return isinstance(node.func, ast.Attribute) and node.func.attr == "HTTPException"


def _bare_stringified_http_exception_mappings() -> list[str]:
    offenders: list[str] = []
    for directory in (WEB_DIR, API_DIR):
        for path in sorted(directory.rglob("*.py")):
            tree = ast.parse(_text(path), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Raise):
                    continue
                if node.cause is not None or not _is_http_exception_call(node.exc):
                    continue
                assert isinstance(node.exc, ast.Call)
                detail = next(
                    (
                        keyword.value
                        for keyword in node.exc.keywords
                        if keyword.arg == "detail"
                    ),
                    None,
                )
                if detail is not None and _is_stringified_exception_detail(detail):
                    offenders.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}:"
                        "bare stringified HTTPException detail"
                    )
    return offenders


def test_plan_records_post_exception_chaining_closeout_without_unlocking_phase5() -> None:
    plan = _text(PLAN)
    flat_plan = _flat_markdown(plan)

    for phrase in (
        "**2026-05-14 status refresh**",
        "Direct residual router exception chaining landed",
        "`main=99a9fd7`",
        "This refresh broadens the guard to f-string and `repr(...)` style stringified `HTTPException` details",
        "The resulting invariant covers `src/yuantus/meta_engine/web` and `src/yuantus/api` with no bare stringified `HTTPException` mappings without `from e` / `from exc`",
        "does not change the Phase 5 gate",
        "Phase 5 remains blocked until accepted real P3.4 external PostgreSQL rehearsal evidence is recorded",
        "| 技术债：router exception chaining | ✅ Done |",
        "Concrete code-level findings supporting the assessment after the 2026-05-14 refresh:",
    ):
        assert phrase in flat_plan


def test_router_web_and_api_have_no_bare_stringified_http_exception_mappings() -> None:
    assert _bare_stringified_http_exception_mappings() == []


def test_residual_closeout_contract_remains_ci_wired() -> None:
    residual_contract = _text(RESIDUAL_CLOSEOUT_CONTRACT)
    ci_yml = _text(CI_YML)

    assert "WEB_DIR" in residual_contract
    assert "API_DIR" in residual_contract
    assert "detail=str(" in residual_contract
    assert " from " in residual_contract
    assert "test_residual_router_exception_chaining_closeout.py" in ci_yml
    assert "test_next_cycle_post_exception_chaining_status_contracts.py" in ci_yml


def test_dev_verification_md_is_indexed_and_keeps_scope_narrow() -> None:
    md = _text(DEV_VERIFICATION_MD)
    index = _text(DOC_INDEX)
    doc_path = str(DEV_VERIFICATION_MD.relative_to(ROOT))

    assert doc_path in index
    assert doc_path in md
    assert "only changes two runtime lines" in md
    assert "No Phase 5 implementation." in md
    assert "No P3.4 evidence synthesis or cutover enablement." in md
    assert "Claude Code was used read-only" in md
