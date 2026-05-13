from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import document_sync_freshness_router as freshness_module


ROOT = Path(__file__).resolve().parents[4]
FRESHNESS_ROUTER = ROOT / "src/yuantus/meta_engine/web/document_sync_freshness_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_FRESHNESS_ROUTER_EXCEPTION_CHAINING_20260513.md"
)


class FailingDocumentSyncService:
    def __init__(self, db: object) -> None:
        self.db = db

    def site_freshness(self, site_id: str) -> object:
        raise ValueError(f"site freshness not found: {site_id}")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_site_freshness_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        freshness_module,
        "DocumentSyncService",
        FailingDocumentSyncService,
    )

    with pytest.raises(HTTPException) as exc_info:
        freshness_module.site_freshness(
            site_id="site-1",
            db=MagicMock(),
            user=MagicMock(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "site freshness not found: site-1"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_document_sync_freshness_router_exception_chaining_is_source_pinned() -> None:
    source = _source(FRESHNESS_ROUTER)

    assert (
        source.count("raise HTTPException(status_code=404, detail=str(exc)) from exc")
        == 1
    )


def test_document_sync_freshness_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_document_sync_freshness_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
