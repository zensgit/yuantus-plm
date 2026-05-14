from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from yuantus.meta_engine.version.file_service import VersionFileError
from yuantus.meta_engine.version.service import VersionError
from yuantus.meta_engine.web import version_file_router
from yuantus.meta_engine.web import version_iteration_router
from yuantus.meta_engine.web import version_lifecycle_router


ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = ROOT / "src/yuantus/meta_engine/web"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
DEV_VERIFICATION_DOC = (
    "docs/DEV_AND_VERIFICATION_VERSION_ROUTER_EXCEPTION_CHAINING_CLOSEOUT_20260514.md"
)

EXPECTED_LINES = {
    "version_file_router.py": [
        "raise HTTPException(status_code=404, detail=str(e)) from e",
        "raise HTTPException(status_code=400, detail=str(e)) from e",
        "raise HTTPException(status_code=400, detail=detail) from exc",
        "raise HTTPException(status_code=404, detail=detail) from exc",
        "raise HTTPException(status_code=409, detail=detail) from exc",
    ],
    "version_iteration_router.py": [
        "raise HTTPException(status_code=400, detail=str(e)) from e",
    ],
    "version_lifecycle_router.py": [
        "raise HTTPException(status_code=400, detail=str(e)) from e",
        "raise HTTPException(status_code=400, detail=detail) from exc",
        "raise HTTPException(status_code=404, detail=detail) from exc",
        "raise HTTPException(status_code=409, detail=detail) from exc",
    ],
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_version_file_detail_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingFileService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def get_version_detail(self, *_args: object, **_kwargs: object) -> object:
            raise VersionFileError("Version ver-1 not found")

    monkeypatch.setattr(version_file_router, "VersionFileService", FailingFileService)

    with pytest.raises(HTTPException) as exc_info:
        version_file_router.get_version_detail("ver-1", db=MagicMock())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Version ver-1 not found"
    assert isinstance(exc_info.value.__cause__, VersionFileError)


def test_version_file_thumbnail_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(
        id="ver-1",
        is_released=False,
        checked_out_by_id=7,
    )

    class FailingFileService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def set_thumbnail(self, *_args: object, **_kwargs: object) -> object:
            raise VersionFileError("thumbnail rejected")

    monkeypatch.setattr(version_file_router, "VersionFileService", FailingFileService)

    with pytest.raises(HTTPException) as exc_info:
        version_file_router.set_version_thumbnail(
            "ver-1",
            version_file_router.SetThumbnailRequest(thumbnail_data="base64"),
            user_id=7,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "thumbnail rejected"
    assert isinstance(exc_info.value.__cause__, VersionFileError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_version_iteration_create_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingIterationService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def create_iteration(self, *_args: object, **_kwargs: object) -> object:
            raise VersionError("iteration rejected")

    monkeypatch.setattr(
        version_iteration_router,
        "IterationService",
        FailingIterationService,
    )

    with pytest.raises(HTTPException) as exc_info:
        version_iteration_router.create_iteration(
            "ver-1",
            version_iteration_router.CreateIterationRequest(),
            user_id=7,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "iteration rejected"
    assert isinstance(exc_info.value.__cause__, VersionError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_version_lifecycle_checkout_helper_failure_preserves_exception_cause_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()

    class FailingVersionService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def checkout(self, *_args: object, **_kwargs: object) -> object:
            raise VersionError("Version ver-1 is checked out by another user")

    monkeypatch.setattr(
        version_lifecycle_router,
        "VersionService",
        FailingVersionService,
    )

    with pytest.raises(HTTPException) as exc_info:
        version_lifecycle_router.checkout(
            "item-1",
            response=MagicMock(),
            user_id=7,
            comment=None,
            version_id=None,
            doc_sync_site_id=None,
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Version ver-1 is checked out by another user"
    assert isinstance(exc_info.value.__cause__, VersionError)
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_version_lifecycle_compare_failure_preserves_exception_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingVersionService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def compare_versions(self, *_args: object, **_kwargs: object) -> object:
            raise VersionError("compare rejected")

    monkeypatch.setattr(
        version_lifecycle_router,
        "VersionService",
        FailingVersionService,
    )

    with pytest.raises(HTTPException) as exc_info:
        version_lifecycle_router.compare_versions("v1", "v2", db=MagicMock())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "compare rejected"
    assert isinstance(exc_info.value.__cause__, VersionError)


def test_version_router_exception_chaining_is_source_pinned() -> None:
    for filename, expected_lines in EXPECTED_LINES.items():
        source = _source(WEB_DIR / filename)
        for expected_line in expected_lines:
            assert expected_line in source


def test_version_router_family_has_no_bare_stringified_exception_mappings() -> None:
    offenders: list[str] = []
    for path in sorted(WEB_DIR.glob("version*_router.py")):
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


def test_version_exception_chaining_contract_is_ci_wired_and_doc_indexed() -> None:
    workflow = _source(CI_WORKFLOW)
    index = _source(DOC_INDEX)

    assert (
        "src/yuantus/meta_engine/tests/test_version_router_exception_chaining_closeout.py"
        in workflow
    )
    assert DEV_VERIFICATION_DOC in index
