from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.web import document_sync_core_router as core_module


ROOT = Path(__file__).resolve().parents[4]
CORE_ROUTER = ROOT / "src/yuantus/meta_engine/web/document_sync_core_router.py"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_CORE_ROUTER_EXCEPTION_CHAINING_20260513.md"
)


class FailingDocumentSyncService:
    def __init__(self, db: object) -> None:
        self.db = db

    def create_site(self, **_kwargs: object) -> object:
        raise ValueError("invalid site request")

    def mirror_probe(self, site_id: str) -> object:
        raise ValueError(f"mirror probe failed: {site_id}")

    def mirror_execute(self, site_id: str) -> object:
        raise ValueError(f"mirror execute failed: {site_id}")

    def create_job(self, **_kwargs: object) -> object:
        raise ValueError("invalid job request")

    def job_summary(self, job_id: str) -> object:
        raise ValueError(f"job summary not found: {job_id}")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    return user


@pytest.mark.parametrize(
    ("call_name", "expected_detail"),
    [
        ("create_site", "invalid site request"),
        ("mirror_probe_site", "mirror probe failed: site-1"),
        ("mirror_execute_site", "mirror execute failed: site-1"),
        ("create_job", "invalid job request"),
    ],
)
def test_document_sync_core_400_failures_preserve_original_exception(
    monkeypatch: pytest.MonkeyPatch,
    call_name: str,
    expected_detail: str,
) -> None:
    monkeypatch.setattr(
        core_module,
        "DocumentSyncService",
        FailingDocumentSyncService,
    )
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        if call_name == "create_site":
            core_module.create_site(
                request=core_module.SiteCreateRequest(
                    name="Site 1",
                    site_code="site-1",
                ),
                db=db,
                user=_user(),
            )
        elif call_name == "mirror_probe_site":
            core_module.mirror_probe_site(
                site_id="site-1",
                db=db,
                user=_user(),
            )
        elif call_name == "mirror_execute_site":
            core_module.mirror_execute_site(
                site_id="site-1",
                db=db,
                user=_user(),
            )
        elif call_name == "create_job":
            core_module.create_job(
                request=core_module.JobCreateRequest(site_id="site-1"),
                db=db,
                user=_user(),
            )
        else:  # pragma: no cover - guarded by parametrization.
            raise AssertionError(f"unexpected call: {call_name}")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail
    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.parametrize("call_name", ["create_site", "mirror_execute_site", "create_job"])
def test_document_sync_core_write_failures_still_roll_back(
    monkeypatch: pytest.MonkeyPatch,
    call_name: str,
) -> None:
    monkeypatch.setattr(
        core_module,
        "DocumentSyncService",
        FailingDocumentSyncService,
    )
    db = MagicMock()

    with pytest.raises(HTTPException):
        if call_name == "create_site":
            core_module.create_site(
                request=core_module.SiteCreateRequest(
                    name="Site 1",
                    site_code="site-1",
                ),
                db=db,
                user=_user(),
            )
        elif call_name == "mirror_execute_site":
            core_module.mirror_execute_site(
                site_id="site-1",
                db=db,
                user=_user(),
            )
        elif call_name == "create_job":
            core_module.create_job(
                request=core_module.JobCreateRequest(site_id="site-1"),
                db=db,
                user=_user(),
            )
        else:  # pragma: no cover - guarded by parametrization.
            raise AssertionError(f"unexpected call: {call_name}")

    db.rollback.assert_called_once_with()


def test_document_sync_core_job_summary_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        core_module,
        "DocumentSyncService",
        FailingDocumentSyncService,
    )

    with pytest.raises(HTTPException) as exc_info:
        core_module.get_job_summary(
            job_id="job-1",
            db=MagicMock(),
            user=MagicMock(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "job summary not found: job-1"
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_document_sync_core_router_exception_chaining_is_source_pinned() -> None:
    source = _source(CORE_ROUTER)

    assert (
        source.count("raise HTTPException(status_code=400, detail=str(exc)) from exc")
        == 4
    )
    assert (
        source.count("raise HTTPException(status_code=404, detail=str(exc)) from exc")
        == 1
    )


def test_document_sync_core_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_document_sync_core_router_exception_chaining.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
