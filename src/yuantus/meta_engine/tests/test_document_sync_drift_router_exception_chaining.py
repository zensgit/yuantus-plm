from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import document_sync_drift_router as drift_module


ROOT = Path(__file__).resolve().parents[4]
DRIFT_ROUTER = ROOT / "src/yuantus/meta_engine/web/document_sync_drift_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_DRIFT_ROUTER_EXCEPTION_CHAINING_20260513.md"
)


class FailingDocumentSyncService:
    def __init__(self, db: object) -> None:
        self.db = db

    def site_snapshots(self, site_id: str) -> object:
        raise ValueError(f"site not found: {site_id}")

    def job_drift(self, job_id: str) -> object:
        raise ValueError(f"job not found: {job_id}")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_site_snapshots_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(drift_module, "DocumentSyncService", FailingDocumentSyncService)

    with pytest.raises(HTTPException) as exc_info:
        drift_module.site_snapshots(
            site_id="site-1",
            db=MagicMock(),
            user=MagicMock(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "site not found: site-1"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_job_drift_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(drift_module, "DocumentSyncService", FailingDocumentSyncService)

    with pytest.raises(HTTPException) as exc_info:
        drift_module.job_drift(
            job_id="job-1",
            db=MagicMock(),
            user=MagicMock(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "job not found: job-1"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_document_sync_drift_router_exception_chaining_is_source_pinned() -> None:
    source = _source(DRIFT_ROUTER)

    assert (
        source.count("raise HTTPException(status_code=404, detail=str(exc)) from exc")
        == 2
    )


def test_document_sync_drift_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_document_sync_drift_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
