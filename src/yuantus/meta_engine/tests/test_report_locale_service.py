"""Tests for C6 – Report locale profile service."""

from unittest.mock import MagicMock
import pytest

from yuantus.meta_engine.report_locale.models import ReportLocaleProfile, PaperSize
from yuantus.meta_engine.report_locale.service import ReportLocaleService


def _mock_session():
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


class TestReportLocaleService:

    def test_create_profile_defaults(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        p = svc.create_profile(name="Default EN")
        assert p.id
        assert p.lang == "en_US"
        assert p.paper_size == "a4"
        assert p.orientation == "portrait"
        assert p.number_format == "#,##0.00"

    def test_create_profile_chinese(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        p = svc.create_profile(
            name="中文报告",
            lang="zh_CN",
            number_format="#,##0.00",
            date_format="YYYY年MM月DD日",
            timezone="Asia/Shanghai",
            paper_size="a4",
        )
        assert p.lang == "zh_CN"
        assert p.timezone == "Asia/Shanghai"

    def test_create_profile_invalid_paper_size_raises(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        with pytest.raises(ValueError, match="Invalid paper_size"):
            svc.create_profile(name="Bad", paper_size="a5")

    def test_create_profile_invalid_orientation_raises(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        with pytest.raises(ValueError, match="Invalid orientation"):
            svc.create_profile(name="Bad", orientation="diagonal")

    def test_get_profile(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        p = svc.create_profile(name="Test Profile")
        found = svc.get_profile(p.id)
        assert found is p

    def test_update_profile(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        p = svc.create_profile(name="Old Name")
        updated = svc.update_profile(
            p.id, name="New Name", paper_size="letter"
        )
        assert updated.name == "New Name"
        assert updated.paper_size == "letter"

    def test_update_nonexistent_returns_none(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        result = svc.update_profile("nonexistent", name="Nothing")
        assert result is None

    def test_delete_profile(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        p = svc.create_profile(name="To Delete")
        assert svc.delete_profile(p.id) is True
        assert svc.get_profile(p.id) is None

    def test_delete_nonexistent_returns_false(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        assert svc.delete_profile("nonexistent") is False

    def test_resolve_profile_exact_match(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        svc.create_profile(
            name="BOM Export ZH",
            lang="zh_CN",
            report_type="bom_export",
        )
        svc.create_profile(
            name="Default ZH",
            lang="zh_CN",
            is_default=True,
        )
        resolved = svc.resolve_profile(lang="zh_CN", report_type="bom_export")
        assert resolved is not None
        assert resolved.report_type == "bom_export"

    def test_resolve_profile_falls_back_to_lang_default(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        svc.create_profile(
            name="Default ZH",
            lang="zh_CN",
            is_default=True,
        )
        resolved = svc.resolve_profile(lang="zh_CN", report_type="quality_report")
        assert resolved is not None
        assert resolved.name == "Default ZH"

    def test_resolve_profile_returns_none_when_no_match(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        resolved = svc.resolve_profile(lang="ja_JP")
        assert resolved is None

    def test_export_context_with_matching_profile(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        svc.create_profile(
            name="BOM ZH",
            lang="zh_CN",
            report_type="bom_export",
            date_format="YYYY年MM月DD日",
            timezone="Asia/Shanghai",
        )
        ctx = svc.get_export_context(lang="zh_CN", report_type="bom_export")
        assert ctx["resolved"] is True
        assert ctx["lang"] == "zh_CN"
        assert ctx["date_format"] == "YYYY年MM月DD日"
        assert ctx["timezone"] == "Asia/Shanghai"
        assert ctx["profile_id"] is not None

    def test_export_context_without_match_returns_defaults(self):
        session = _mock_session()
        svc = ReportLocaleService(session)
        ctx = svc.get_export_context(lang="ja_JP")
        assert ctx["resolved"] is False
        assert ctx["lang"] == "ja_JP"
        assert ctx["number_format"] == "#,##0.00"
        assert ctx["date_format"] == "YYYY-MM-DD"
        assert ctx["profile_id"] is None
