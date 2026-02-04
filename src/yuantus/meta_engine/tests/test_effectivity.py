import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from yuantus.meta_engine.services.effectivity_service import (
    EffectivityService,
    EffectivityContext,
)


class TestEffectivity:
    def _eff(self, **kwargs):
        return SimpleNamespace(**kwargs)

    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_date_check_logic(self, mock_session):
        service = EffectivityService(mock_session)
        now = datetime.utcnow()

        # Range: [Yesterday, Tomorrow]
        eff = self._eff(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            effectivity_type="Date",
        )

        # Inside
        assert (
            service._check_date(eff, EffectivityContext(reference_date=now))
            is True
        )
        # Before
        assert (
            service._check_date(
                eff, EffectivityContext(reference_date=now - timedelta(days=2))
            )
            is False
        )
        # After
        assert (
            service._check_date(
                eff, EffectivityContext(reference_date=now + timedelta(days=2))
            )
            is False
        )

        # Open ended (Start only)
        eff_start = self._eff(
            start_date=now, end_date=None, effectivity_type="Date"
        )
        assert (
            service._check_date(
                eff_start,
                EffectivityContext(reference_date=now + timedelta(seconds=1)),
            )
            is True
        )
        assert (
            service._check_date(
                eff_start,
                EffectivityContext(reference_date=now - timedelta(seconds=1)),
            )
            is False
        )

    def test_check_effectivity_query(self, mock_session):
        service = EffectivityService(mock_session)
        now = datetime.utcnow()

        # Mock DB return: One valid record
        eff = self._eff(
            id="E1",
            item_id="I1",
            effectivity_type="Date",
            start_date=now - timedelta(days=10),
            end_date=now + timedelta(days=10),
        )

        mock_session.query.return_value.filter.return_value.all.return_value = [eff]

        # Valid date
        assert service.check_date_effectivity("I1", now) is True

        # Invalid date (loop check)
        # Assuming query returns same object (mock behavior)
        # The logic inside check_date_effectivity calls _check_date on the result.
        # So passing a date outside range should return False
        assert service.check_date_effectivity("I1", now + timedelta(days=20)) is False

    def test_no_effectivity_implies_valid(self, mock_session):
        service = EffectivityService(mock_session)
        # Empty list
        mock_session.query.return_value.filter.return_value.all.return_value = []

        assert service.check_date_effectivity("I2", datetime.utcnow()) is True

    def test_lot_effectivity_range(self, mock_session):
        service = EffectivityService(mock_session)
        eff = self._eff(
            effectivity_type="Lot",
            payload={"lot_start": "L010", "lot_end": "L020"},
        )
        assert (
            service._check_lot(eff, EffectivityContext(lot_number="L015")) is True
        )
        assert (
            service._check_lot(eff, EffectivityContext(lot_number="L005")) is False
        )
        assert (
            service._check_lot(eff, EffectivityContext(lot_number="L030")) is False
        )

    def test_serial_effectivity_list(self, mock_session):
        service = EffectivityService(mock_session)
        eff = self._eff(
            effectivity_type="Serial",
            payload={"serials": ["SN-1", "SN-2"]},
        )
        assert (
            service._check_serial(eff, EffectivityContext(serial_number="SN-1"))
            is True
        )
        assert (
            service._check_serial(eff, EffectivityContext(serial_number="SN-9"))
            is False
        )
