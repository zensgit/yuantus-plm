from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Response

from yuantus.meta_engine.web import file_conversion_router
from yuantus.meta_engine.web import file_storage_router


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_FILE_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md"
)

EXPECTED_LINES = {
    "file_conversion_router.py": [
        "raise HTTPException(status_code=500, detail=str(e)) from e",
    ],
    "file_storage_router.py": [
        "raise HTTPException(status_code=500, detail=str(e)) from e",
    ],
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _cad_file(file_id: str = "file-1") -> SimpleNamespace:
    return SimpleNamespace(
        id=file_id,
        filename="part.stp",
        is_cad_file=lambda: True,
    )


def test_file_conversion_request_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.return_value = _cad_file()

    def fail_queue(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(file_conversion_router, "_queue_file_conversion_job", fail_queue)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            file_conversion_router.request_conversion(
                "file-1",
                target_format="gltf",
                db=db,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "queue unavailable"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()


def test_file_conversion_process_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingJobService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def requeue_stale_jobs(self) -> object:
            raise RuntimeError("job queue unavailable")

    monkeypatch.setattr(file_conversion_router, "JobService", FailingJobService)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(file_conversion_router.process_conversion_queue(batch_size=10, db=db))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "job queue unavailable"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()


def test_file_conversion_legacy_process_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.return_value = _cad_file()

    def fail_queue(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("legacy queue unavailable")

    monkeypatch.setattr(file_conversion_router, "_queue_file_conversion_job", fail_queue)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            file_conversion_router.process_cad_legacy(
                {"file_id": "file-1", "target_format": "gltf"},
                response=Response(),
                db=db,
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "legacy queue unavailable"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()


def test_file_storage_upload_failure_preserves_exception_cause_and_rollback() -> None:
    db = MagicMock()

    class FailingUploadFile:
        filename = "part.stp"

        async def read(self) -> bytes:
            raise RuntimeError("read failed")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            file_storage_router.upload_file(
                Response(),
                file=FailingUploadFile(),
                db=db,
                identity_db=MagicMock(),
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "read failed"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_called_once_with()


def test_file_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_lines in EXPECTED_LINES.items():
        source = _source(WEB_DIR / filename)
        for expected_line in expected_lines:
            assert expected_line in source


def test_file_router_family_has_no_bare_stringified_exception_mappings() -> None:
    offenders: list[str] = []
    for path in sorted(WEB_DIR.glob("file*_router.py")):
        source = _source(path)
        for line_no, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if (
                stripped.startswith("raise HTTPException(")
                and "detail=str(" in stripped
                and " from " not in stripped
            ):
                offenders.append(f"{path.name}:{line_no}:{stripped}")

    assert offenders == []


def test_file_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    doc_index = _source(DOC_INDEX)

    assert "test_file_router_exception_chaining_closeout.py" in workflow
    assert DEV_VERIFICATION_DOC in doc_index
    assert (ROOT / DEV_VERIFICATION_DOC).exists()
