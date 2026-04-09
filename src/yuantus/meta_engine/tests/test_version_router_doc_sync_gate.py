from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db


def _client_with_user_id(user_id: int):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_user_id():
        return user_id

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_get_user_id
    return TestClient(app), mock_db_session


def test_version_checkout_blocked_by_doc_sync_gate():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            doc_sync_cls.return_value.evaluate_checkout_sync_gate.return_value = {
                "item_id": "item-1",
                "site_id": "site-a",
                "blocking": True,
                "blocking_total": 2,
                "blocking_counts": {
                    "pending": 1,
                    "processing": 1,
                    "failed": 0,
                    "dead_letter": 0,
                },
                "blocking_jobs": [{"id": "job-1"}, {"id": "job-2"}],
            }
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={"doc_sync_site_id": "site-a"},
            )

    assert resp.status_code == 409
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "doc_sync_checkout_blocked"
    assert detail.get("context", {}).get("blocking") is True
    assert detail.get("context", {}).get("blocking_total") == 2
    assert not db.commit.called
    doc_sync_cls.return_value.evaluate_checkout_sync_gate.assert_called_once_with(
        item_id="item-1",
        site_id="site-a",
        version_id=None,
        document_ids=["item-1"],
        window_days=7,
        limit=200,
        block_on_dead_letter_only=False,
        max_pending=0,
        max_processing=0,
        max_failed=0,
        max_dead_letter=0,
    )
    assert version_cls.return_value.checkout.call_count == 0


def test_version_checkout_allows_warn_mode_with_header_when_gate_blocks():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            doc_sync_cls.return_value.evaluate_checkout_sync_gate.return_value = {
                "item_id": "item-1",
                "site_id": "site-a",
                "blocking": True,
                "blocking_total": 2,
                "blocking_counts": {
                    "pending": 1,
                    "processing": 1,
                    "failed": 0,
                    "dead_letter": 0,
                },
                "blocking_jobs": [{"id": "job-1"}, {"id": "job-2"}],
            }
            version_cls.return_value.checkout.return_value = {
                "id": "ver-allowed",
                "item_id": "item-1",
            }
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={
                    "doc_sync_site_id": "site-a",
                    "doc_sync_strictness_mode": "warn",
                },
            )

    assert resp.status_code == 200
    assert resp.headers.get("X-Doc-Sync-Checkout-Warning") == (
        "Checkout allowed despite doc-sync backlog"
    )
    assert resp.json()["id"] == "ver-allowed"
    assert db.commit.called
    doc_sync_cls.return_value.evaluate_checkout_sync_gate.assert_called_once_with(
        item_id="item-1",
        site_id="site-a",
        version_id=None,
        document_ids=["item-1"],
        window_days=7,
        limit=200,
        block_on_dead_letter_only=False,
        max_pending=0,
        max_processing=0,
        max_failed=0,
        max_dead_letter=0,
    )
    version_cls.return_value.checkout.assert_called_once_with(
        "item-1",
        7,
        None,
        None,
    )


def test_version_checkout_explicit_block_mode_keeps_409_behavior():
    client, db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            doc_sync_cls.return_value.evaluate_checkout_sync_gate.return_value = {
                "item_id": "item-1",
                "site_id": "site-a",
                "blocking": True,
                "blocking_total": 1,
                "blocking_counts": {
                    "pending": 1,
                    "processing": 0,
                    "failed": 0,
                    "dead_letter": 0,
                },
                "blocking_jobs": [{"id": "job-1"}],
            }
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={
                    "doc_sync_site_id": "site-a",
                    "doc_sync_strictness_mode": "block",
                },
            )

    assert resp.status_code == 409
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "doc_sync_checkout_blocked"
    assert detail.get("context", {}).get("blocking") is True
    assert detail.get("context", {}).get("blocking_total") == 1
    assert not db.commit.called
    doc_sync_cls.return_value.evaluate_checkout_sync_gate.assert_called_once_with(
        item_id="item-1",
        site_id="site-a",
        version_id=None,
        document_ids=["item-1"],
        window_days=7,
        limit=200,
        block_on_dead_letter_only=False,
        max_pending=0,
        max_processing=0,
        max_failed=0,
        max_dead_letter=0,
    )
    assert version_cls.return_value.checkout.call_count == 0


def test_version_checkout_doc_sync_gate_invalid_maps_400():
    client, _db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            doc_sync_cls.return_value.evaluate_checkout_sync_gate.side_effect = ValueError(
                "window_days must be between 1 and 90"
            )
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={
                    "doc_sync_site_id": "site-a",
                    "doc_sync_window_days": 0,
                },
            )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "doc_sync_checkout_gate_invalid"
    assert detail.get("context", {}).get("site_id") == "site-a"
    assert detail.get("context", {}).get("window_days") == 0
    assert detail.get("context", {}).get("block_on_dead_letter_only") is False
    assert detail.get("context", {}).get("max_dead_letter") == 0
    doc_sync_cls.return_value.evaluate_checkout_sync_gate.assert_called_once_with(
        item_id="item-1",
        site_id="site-a",
        version_id=None,
        document_ids=["item-1"],
        window_days=0,
        limit=200,
        block_on_dead_letter_only=False,
        max_pending=0,
        max_processing=0,
        max_failed=0,
        max_dead_letter=0,
    )
    assert version_cls.return_value.checkout.call_count == 0


def test_version_checkout_doc_sync_strictness_mode_invalid_maps_400():
    client, _db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={
                    "doc_sync_site_id": "site-a",
                    "doc_sync_strictness_mode": "maybe",
                },
            )

    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "doc_sync_checkout_gate_invalid"
    assert detail.get("context", {}).get("mode") == "maybe"
    assert detail.get("context", {}).get("allowed_modes") == ["block", "warn"]
    assert doc_sync_cls.return_value.evaluate_checkout_sync_gate.call_count == 0
    assert version_cls.return_value.checkout.call_count == 0


def test_version_checkout_passes_when_doc_sync_gate_clear():
    client, db = _client_with_user_id(7)
    db.get.return_value = None

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            doc_sync_cls.return_value.evaluate_checkout_sync_gate.return_value = {
                "item_id": "item-1",
                "site_id": "site-a",
                "blocking": False,
                "blocking_total": 0,
                "blocking_counts": {
                    "pending": 0,
                    "processing": 0,
                    "failed": 0,
                    "dead_letter": 0,
                },
                "blocking_jobs": [],
            }
            version_cls.return_value.checkout.return_value = {
                "id": "ver-1",
                "item_id": "item-1",
            }
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={
                    "comment": "cad edit",
                    "version_id": "v-main",
                    "doc_sync_site_id": "site-a",
                    "doc_sync_window_days": 3,
                    "doc_sync_limit": 10,
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "ver-1"
    assert db.commit.called
    doc_sync_cls.return_value.evaluate_checkout_sync_gate.assert_called_once_with(
        item_id="item-1",
        site_id="site-a",
        version_id="v-main",
        document_ids=["v-main"],
        window_days=3,
        limit=10,
        block_on_dead_letter_only=False,
        max_pending=0,
        max_processing=0,
        max_failed=0,
        max_dead_letter=0,
    )
    version_cls.return_value.checkout.assert_called_once_with(
        "item-1",
        7,
        "cad edit",
        "v-main",
    )


def test_version_checkout_gate_includes_version_files_and_extra_document_ids():
    client, db = _client_with_user_id(7)
    db.get.return_value = SimpleNamespace(
        item_id="item-1",
        primary_file_id="file-primary",
        version_files=[
            SimpleNamespace(file_id="file-a"),
            SimpleNamespace(file_id="file-b"),
        ],
    )

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            doc_sync_cls.return_value.evaluate_checkout_sync_gate.return_value = {
                "item_id": "item-1",
                "site_id": "site-a",
                "blocking": False,
                "blocking_total": 0,
                "blocking_counts": {
                    "pending": 0,
                    "processing": 0,
                    "failed": 0,
                    "dead_letter": 0,
                },
                "blocking_jobs": [],
            }
            version_cls.return_value.checkout.return_value = {"id": "ver-2"}
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={
                    "version_id": "v-main",
                    "doc_sync_site_id": "site-a",
                    "doc_sync_document_ids": ["file-c"],
                },
            )

    assert resp.status_code == 200
    doc_sync_cls.return_value.evaluate_checkout_sync_gate.assert_called_once_with(
        item_id="item-1",
        site_id="site-a",
        version_id="v-main",
        document_ids=[
            "file-a",
            "file-b",
            "file-c",
            "file-primary",
            "v-main",
        ],
        window_days=7,
        limit=200,
        block_on_dead_letter_only=False,
        max_pending=0,
        max_processing=0,
        max_failed=0,
        max_dead_letter=0,
    )


def test_version_checkout_doc_sync_gate_supports_dead_letter_policy_thresholds():
    client, _db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.version_router.DocumentMultiSiteService") as doc_sync_cls:
        with patch("yuantus.meta_engine.web.version_router.VersionService") as version_cls:
            doc_sync_cls.return_value.evaluate_checkout_sync_gate.return_value = {
                "item_id": "item-1",
                "site_id": "site-a",
                "blocking": True,
                "blocking_total": 1,
                "blocking_counts": {
                    "pending": 2,
                    "processing": 0,
                    "failed": 1,
                    "dead_letter": 1,
                },
                "policy": {"block_on_dead_letter_only": True},
                "thresholds": {
                    "pending": 5,
                    "processing": 5,
                    "failed": 5,
                    "dead_letter": 0,
                },
                "blocking_reasons": [
                    {"status": "dead_letter", "count": 1, "threshold": 0}
                ],
                "blocking_jobs": [{"id": "job-dl-1"}],
            }
            resp = client.post(
                "/api/v1/versions/items/item-1/checkout",
                json={
                    "doc_sync_site_id": "site-a",
                    "doc_sync_block_on_dead_letter_only": True,
                    "doc_sync_max_pending": 5,
                    "doc_sync_max_processing": 5,
                    "doc_sync_max_failed": 5,
                    "doc_sync_max_dead_letter": 0,
                },
            )

    assert resp.status_code == 409
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "doc_sync_checkout_blocked"
    assert detail.get("message") == "Checkout blocked by doc-sync dead-letter backlog"
    doc_sync_cls.return_value.evaluate_checkout_sync_gate.assert_called_once_with(
        item_id="item-1",
        site_id="site-a",
        version_id=None,
        document_ids=["item-1"],
        window_days=7,
        limit=200,
        block_on_dead_letter_only=True,
        max_pending=5,
        max_processing=5,
        max_failed=5,
        max_dead_letter=0,
    )
    assert version_cls.return_value.checkout.call_count == 0
