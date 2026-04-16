from unittest.mock import MagicMock
import pytest
from yuantus.meta_engine.version.file_service import (
    VersionFileError, VersionFileService,
)


def _mock_version(*, released=False, checked_out_by_id=None):
    v = MagicMock()
    v.is_released = released
    v.checked_out_by_id = checked_out_by_id
    return v


def _mock_vf(*, checked_out_by_id=None):
    vf = MagicMock()
    vf.id = "vf-1"; vf.version_id = "v1"; vf.file_id = "f1"
    vf.file_role = "native_cad"
    vf.checked_out_by_id = checked_out_by_id
    vf.checked_out_at = None
    return vf


def test_checkout_file_locks_unlocked_vf():
    s = MagicMock(); v = _mock_version(); vf = _mock_vf()
    s.get.return_value = v
    s.query.return_value.filter_by.return_value.first.return_value = vf
    svc = VersionFileService(s)
    r = svc.checkout_file("v1", "f1", user_id=7)
    assert r is vf
    assert vf.checked_out_by_id == 7


def test_checkout_file_idempotent_same_user():
    s = MagicMock(); v = _mock_version(); vf = _mock_vf(checked_out_by_id=7)
    s.get.return_value = v
    s.query.return_value.filter_by.return_value.first.return_value = vf
    svc = VersionFileService(s)
    r = svc.checkout_file("v1", "f1", user_id=7)
    assert r is vf


def test_checkout_file_rejects_other_user():
    s = MagicMock(); v = _mock_version(); vf = _mock_vf(checked_out_by_id=8)
    s.get.return_value = v
    s.query.return_value.filter_by.return_value.first.return_value = vf
    svc = VersionFileService(s)
    with pytest.raises(VersionFileError, match="checked out by another user"):
        svc.checkout_file("v1", "f1", user_id=7)


def test_checkout_file_rejects_released_version():
    s = MagicMock(); v = _mock_version(released=True)
    s.get.return_value = v
    svc = VersionFileService(s)
    with pytest.raises(VersionFileError, match="released"):
        svc.checkout_file("v1", "f1", user_id=7)


def test_undo_checkout_clears_lock_for_same_user():
    s = MagicMock(); vf = _mock_vf(checked_out_by_id=7)
    s.query.return_value.filter_by.return_value.first.return_value = vf
    svc = VersionFileService(s)
    svc.undo_checkout_file("v1", "f1", user_id=7)
    assert vf.checked_out_by_id is None


def test_undo_checkout_rejects_other_user():
    s = MagicMock(); vf = _mock_vf(checked_out_by_id=8)
    s.query.return_value.filter_by.return_value.first.return_value = vf
    svc = VersionFileService(s)
    with pytest.raises(VersionFileError):
        svc.undo_checkout_file("v1", "f1", user_id=7)


def test_get_file_lock_returns_state():
    s = MagicMock(); vf = _mock_vf(checked_out_by_id=7)
    s.query.return_value.filter_by.return_value.first.return_value = vf
    svc = VersionFileService(s)
    r = svc.get_file_lock("v1", "f1")
    assert r["checked_out_by_id"] == 7


def test_assert_file_unlocked_raises_on_other_user():
    s = MagicMock(); vf = _mock_vf(checked_out_by_id=8)
    s.query.return_value.filter.return_value.all.return_value = [vf]
    svc = VersionFileService(s)
    with pytest.raises(VersionFileError):
        svc.assert_file_unlocked("f1", user_id=7)
