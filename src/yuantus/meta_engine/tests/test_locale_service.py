"""Tests for C6 – Locale translation storage service."""

from unittest.mock import MagicMock
import pytest

from yuantus.meta_engine.locale.models import Translation, TranslationState
from yuantus.meta_engine.locale.service import LocaleService


def _mock_session():
    """Session mock with in-memory store for add/get/query/delete."""
    session = MagicMock()
    _store = {}

    def mock_add(obj):
        _store[obj.id] = obj

    def mock_get(model, obj_id):
        obj = _store.get(obj_id)
        if obj and isinstance(obj, model):
            return obj
        return None

    def mock_delete(obj):
        _store.pop(obj.id, None)

    def mock_flush():
        pass

    # query().filter().first() / .all() chains
    class MockQuery:
        def __init__(self, model):
            self._model = model
            self._filters = []

        def filter(self, *args):
            self._filters.extend(args)
            return self

        def order_by(self, *args):
            return self

        def first(self):
            # Simple matching on Translation attributes
            for obj in _store.values():
                if not isinstance(obj, self._model):
                    continue
                if self._match(obj):
                    return obj
            return None

        def all(self):
            return [
                obj
                for obj in _store.values()
                if isinstance(obj, self._model) and self._match(obj)
            ]

        def _match(self, obj):
            for f in self._filters:
                # SQLAlchemy BinaryExpression: f.left.key, f.right.effective_value
                try:
                    col_name = f.left.key
                    expected = f.right.effective_value
                    if getattr(obj, col_name, None) != expected:
                        return False
                except AttributeError:
                    pass
            return True

    def mock_query(model):
        return MockQuery(model)

    session.add.side_effect = mock_add
    session.get.side_effect = mock_get
    session.delete.side_effect = mock_delete
    session.flush.side_effect = mock_flush
    session.query.side_effect = mock_query
    session._store = _store
    return session


class TestLocaleService:

    def test_upsert_creates_new(self):
        session = _mock_session()
        svc = LocaleService(session)
        t = svc.upsert_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="zh_CN",
            translated_value="螺栓 M10",
            source_value="Bolt M10",
        )
        assert t.id
        assert t.translated_value == "螺栓 M10"
        assert t.source_value == "Bolt M10"
        assert t.state == "draft"

    def test_upsert_updates_existing(self):
        session = _mock_session()
        svc = LocaleService(session)
        t1 = svc.upsert_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="zh_CN",
            translated_value="螺栓",
        )
        t2 = svc.upsert_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="zh_CN",
            translated_value="螺栓 M10 已更新",
            state="approved",
        )
        assert t2.id == t1.id
        assert t2.translated_value == "螺栓 M10 已更新"
        assert t2.state == "approved"

    def test_upsert_invalid_state_raises(self):
        session = _mock_session()
        svc = LocaleService(session)
        with pytest.raises(ValueError, match="Invalid state"):
            svc.upsert_translation(
                record_type="item",
                record_id="itm-1",
                field_name="name",
                lang="en_US",
                translated_value="Test",
                state="invalid",
            )

    def test_get_translation(self):
        session = _mock_session()
        svc = LocaleService(session)
        svc.upsert_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="de_DE",
            translated_value="Schraube M10",
        )
        found = svc.get_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="de_DE",
        )
        assert found is not None
        assert found.translated_value == "Schraube M10"

    def test_get_translations_for_record(self):
        session = _mock_session()
        svc = LocaleService(session)
        svc.upsert_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="zh_CN",
            translated_value="螺栓",
        )
        svc.upsert_translation(
            record_type="item",
            record_id="itm-1",
            field_name="description",
            lang="zh_CN",
            translated_value="M10 六角螺栓",
        )
        items = svc.get_translations_for_record(
            record_type="item", record_id="itm-1"
        )
        assert len(items) == 2

    def test_bulk_upsert(self):
        session = _mock_session()
        svc = LocaleService(session)
        result = svc.bulk_upsert(
            [
                {
                    "record_type": "item",
                    "record_id": "itm-1",
                    "field_name": "name",
                    "lang": "zh_CN",
                    "translated_value": "螺栓",
                },
                {
                    "record_type": "item",
                    "record_id": "itm-2",
                    "field_name": "name",
                    "lang": "zh_CN",
                    "translated_value": "螺母",
                },
            ]
        )
        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["errors"] == []

    def test_delete_translation(self):
        session = _mock_session()
        svc = LocaleService(session)
        svc.upsert_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="fr_FR",
            translated_value="Boulon M10",
        )
        deleted = svc.delete_translation(
            record_type="item",
            record_id="itm-1",
            field_name="name",
            lang="fr_FR",
        )
        assert deleted is True

    def test_delete_nonexistent_returns_false(self):
        session = _mock_session()
        svc = LocaleService(session)
        deleted = svc.delete_translation(
            record_type="item",
            record_id="xxx",
            field_name="name",
            lang="en_US",
        )
        assert deleted is False

    def test_resolve_translation_primary_hit(self):
        session = _mock_session()
        svc = LocaleService(session)
        svc.upsert_translation(
            record_type="item",
            record_id="i1",
            field_name="name",
            lang="zh_CN",
            translated_value="螺栓",
        )
        result = svc.resolve_translation(
            record_type="item",
            record_id="i1",
            field_name="name",
            lang="zh_CN",
            fallback_langs=["en_US"],
        )
        assert result["resolved"] is True
        assert result["value"] == "螺栓"
        assert result["resolved_from_lang"] == "zh_CN"
        assert result["chain"][0]["exists"] is True

    def test_resolve_translation_uses_fallback(self):
        session = _mock_session()
        svc = LocaleService(session)
        svc.upsert_translation(
            record_type="item",
            record_id="i1",
            field_name="description",
            lang="en_US",
            translated_value="Hex Bolt M10",
        )
        result = svc.resolve_translation(
            record_type="item",
            record_id="i1",
            field_name="description",
            lang="zh_CN",
            fallback_langs=["en_US"],
        )
        assert result["resolved"] is True
        assert result["value"] == "Hex Bolt M10"
        assert result["resolved_from_lang"] == "en_US"
        assert result["chain"][0]["lang"] == "zh_CN"
        assert result["chain"][1]["lang"] == "en_US"

    def test_resolve_translations_batch_reports_missing_and_fallbacks(self):
        session = _mock_session()
        svc = LocaleService(session)
        svc.upsert_translation(
            record_type="item",
            record_id="i1",
            field_name="name",
            lang="zh_CN",
            translated_value="螺栓",
        )
        svc.upsert_translation(
            record_type="item",
            record_id="i1",
            field_name="description",
            lang="en_US",
            translated_value="Hex Bolt M10",
        )
        result = svc.resolve_translations_batch(
            record_type="item",
            record_id="i1",
            fields=["name", "description", "spec"],
            lang="zh_CN",
            fallback_langs=["en_US"],
        )
        assert len(result["resolved"]) == 2
        assert "spec" in result["missing"]
        assert "en_US" in result["fallbacks_used"]

    def test_fallback_preview_returns_chain(self):
        session = _mock_session()
        svc = LocaleService(session)
        svc.upsert_translation(
            record_type="item",
            record_id="i1",
            field_name="name",
            lang="en_US",
            translated_value="Bolt",
        )
        preview = svc.fallback_preview(
            record_type="item",
            record_id="i1",
            field_name="name",
            lang="zh_CN",
            fallback_langs=["en_US"],
        )
        assert preview["request"]["primary_lang"] == "zh_CN"
        assert preview["resolved_value"] == "Bolt"
        assert preview["resolved_from_lang"] == "en_US"
        assert len(preview["resolution_chain"]) == 2
