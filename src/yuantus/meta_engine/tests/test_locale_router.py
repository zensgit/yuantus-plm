from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import get_db


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    """These tests mock router dependencies directly; middleware auth is out of scope."""
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client_with_db():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), mock_db_session


def test_locale_translation_endpoints_commit_and_list():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.locale_router.LocaleService") as service_cls:
        service = service_cls.return_value
        service.upsert_translation.return_value = SimpleNamespace(
            id="tr-1",
            record_type="item",
            record_id="item-1",
            field_name="name",
            lang="zh_CN",
            source_value="Bolt M10",
            translated_value="螺栓 M10",
            state="draft",
            module="bom",
            created_at=None,
        )
        service.bulk_upsert.return_value = {"created": 2, "updated": 0, "errors": []}
        service.get_translations_for_record.return_value = [service.upsert_translation.return_value]

        create_response = client.post(
            "/api/v1/locale/translations",
            json={
                "record_type": "item",
                "record_id": "item-1",
                "field_name": "name",
                "lang": "zh_CN",
                "translated_value": "螺栓 M10",
                "source_value": "Bolt M10",
                "module": "bom",
            },
        )
        bulk_response = client.post(
            "/api/v1/locale/translations/bulk",
            json={
                "translations": [
                    {
                        "record_type": "item",
                        "record_id": "item-1",
                        "field_name": "name",
                        "lang": "zh_CN",
                        "translated_value": "螺栓",
                    },
                    {
                        "record_type": "item",
                        "record_id": "item-2",
                        "field_name": "name",
                        "lang": "zh_CN",
                        "translated_value": "螺母",
                    },
                ]
            },
        )
        list_response = client.get(
            "/api/v1/locale/translations?record_type=item&record_id=item-1"
        )

    assert create_response.status_code == 200
    assert create_response.json()["id"] == "tr-1"
    assert bulk_response.status_code == 200
    assert bulk_response.json()["created"] == 2
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert db.commit.call_count == 2


def test_report_locale_profile_endpoints_commit_and_resolve():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.locale_router.ReportLocaleService") as service_cls:
        service = service_cls.return_value
        profile = SimpleNamespace(
            id="rp-1",
            name="BOM Export ZH",
            lang="zh_CN",
            fallback_lang=None,
            number_format="#,##0.00",
            date_format="YYYY-MM-DD",
            time_format="HH:mm:ss",
            timezone="Asia/Shanghai",
            paper_size="a4",
            orientation="portrait",
            header_text=None,
            footer_text=None,
            logo_path=None,
            report_type="bom_export",
            is_default=True,
            created_at=None,
        )
        service.create_profile.return_value = profile
        service.list_profiles.return_value = [profile]
        service.resolve_profile.return_value = profile
        service.delete_profile.return_value = True

        create_response = client.post(
            "/api/v1/locale/report-profiles",
            json={"name": "BOM Export ZH", "lang": "zh_CN", "report_type": "bom_export", "is_default": True},
        )
        list_response = client.get("/api/v1/locale/report-profiles?lang=zh_CN")
        resolve_response = client.get(
            "/api/v1/locale/report-profiles/resolve?lang=zh_CN&report_type=bom_export"
        )
        delete_response = client.delete("/api/v1/locale/report-profiles/rp-1")

    assert create_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert resolve_response.status_code == 200
    assert resolve_response.json()["id"] == "rp-1"
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert db.commit.call_count == 2


def test_locale_resolve_endpoints_return_fallback_payloads():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.locale_router.LocaleService") as service_cls:
        service = service_cls.return_value
        service.resolve_translations_batch.return_value = {
            "resolved": [
                {"field": "name", "lang": "zh_CN", "value": "螺栓"},
                {"field": "description", "lang": "en_US", "value": "Hex Bolt M10"},
            ],
            "missing": [],
            "fallbacks_used": ["en_US"],
        }
        service.fallback_preview.return_value = {
            "request": {
                "record_type": "item",
                "record_id": "item-1",
                "field_name": "name",
                "primary_lang": "zh_CN",
                "fallback_chain": ["en_US"],
            },
            "resolution_chain": [
                {"lang": "zh_CN", "exists": False, "value": None, "source_value": None, "state": None},
                {"lang": "en_US", "exists": True, "value": "Bolt", "source_value": None, "state": "draft"},
            ],
            "resolved_value": "Bolt",
            "resolved_from_lang": "en_US",
        }

        resolve_response = client.post(
            "/api/v1/locale/translations/resolve",
            json={
                "record_type": "item",
                "record_id": "item-1",
                "fields": ["name", "description"],
                "lang": "zh_CN",
                "fallback_langs": ["en_US"],
            },
        )
        preview_response = client.get(
            "/api/v1/locale/translations/fallback-preview"
            "?record_type=item"
            "&record_id=item-1"
            "&field_name=name"
            "&lang=zh_CN"
            "&fallback_langs=en_US"
        )

    assert resolve_response.status_code == 200
    assert resolve_response.json()["fallbacks_used"] == ["en_US"]
    service.resolve_translations_batch.assert_called_once_with(
        record_type="item",
        record_id="item-1",
        fields=["name", "description"],
        lang="zh_CN",
        fallback_langs=["en_US"],
    )
    assert preview_response.status_code == 200
    assert preview_response.json()["resolved_from_lang"] == "en_US"
    service.fallback_preview.assert_called_once_with(
        record_type="item",
        record_id="item-1",
        field_name="name",
        lang="zh_CN",
        fallback_langs=["en_US"],
    )


def test_locale_item_localized_fields_endpoint_resolves_defaults_and_query_lists():
    client, db = _client_with_db()
    item = SimpleNamespace(id="item-1", properties={"description": "Hex bolt"})
    db.get.return_value = item

    with patch("yuantus.meta_engine.web.locale_router.LocaleService") as service_cls:
        service = service_cls.return_value
        service.resolve_item_localized_fields.return_value = {
            "record_type": "item",
            "record_id": "item-1",
            "lang": "zh_CN",
            "fallback_langs": ["en_US", "de_DE"],
            "resolved": [
                {
                    "field": "description",
                    "lang": "en_US",
                    "value": "Hex bolt",
                    "source": "properties_i18n",
                    "chain": [],
                }
            ],
            "missing": [],
            "fallbacks_used": ["en_US"],
        }

        response = client.get(
            "/api/v1/locale/items/item-1/localized-fields"
            "?lang=zh_CN"
            "&fields=name,description"
            "&fallback_langs=en_US,de_DE"
        )

    assert response.status_code == 200
    assert response.json()["resolved"][0]["source"] == "properties_i18n"
    service.resolve_item_localized_fields.assert_called_once_with(
        item,
        fields=["name", "description"],
        lang="zh_CN",
        fallback_langs=["en_US", "de_DE"],
    )


def test_locale_item_localized_fields_endpoint_returns_404_for_missing_item():
    client, db = _client_with_db()
    db.get.return_value = None

    response = client.get(
        "/api/v1/locale/items/missing/localized-fields?lang=zh_CN"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_report_locale_export_context_endpoint_returns_context():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.locale_router.ReportLocaleService") as service_cls:
        service = service_cls.return_value
        service.get_export_context.return_value = {
            "resolved": True,
            "lang": "zh_CN",
            "report_type": "bom_export",
            "profile_id": "rp-ctx-1",
            "profile_name": "BOM ZH",
            "number_format": "#,##0.00",
            "date_format": "YYYY年MM月DD日",
            "time_format": "HH:mm:ss",
            "timezone": "Asia/Shanghai",
            "paper_size": "a4",
            "orientation": "portrait",
            "header_text": None,
            "footer_text": None,
            "logo_path": None,
            "fallback_lang": None,
        }

        response = client.get("/api/v1/locale/export-context?lang=zh_CN&report_type=bom_export")

    assert response.status_code == 200
    assert response.json()["profile_id"] == "rp-ctx-1"
    service.get_export_context.assert_called_once_with(
        lang="zh_CN",
        report_type="bom_export",
    )
