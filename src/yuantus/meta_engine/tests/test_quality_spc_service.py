"""Tests for C16 – QualitySpcService."""
from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from yuantus.meta_engine.quality.spc_service import QualitySpcService


class TestCapabilityIndices:

    def test_basic_capable_process(self):
        # Tight distribution within wide spec limits → high Cpk
        measurements = [10.0, 10.1, 9.9, 10.0, 10.05, 9.95, 10.02, 9.98]
        svc = QualitySpcService(measurements, lsl=9.0, usl=11.0)
        result = svc.capability_indices()
        assert result["cp"] is not None
        assert result["cpk"] is not None
        assert result["is_capable"] is True
        assert result["sample_size"] == 8

    def test_incapable_process(self):
        # Wide distribution relative to spec limits
        measurements = [5.0, 15.0, 3.0, 17.0, 8.0, 12.0]
        svc = QualitySpcService(measurements, lsl=9.0, usl=11.0)
        result = svc.capability_indices()
        assert result["is_capable"] is False

    def test_single_measurement(self):
        svc = QualitySpcService([10.0], lsl=9.0, usl=11.0)
        result = svc.capability_indices()
        assert result["cp"] is None
        assert result["cpk"] is None
        assert result["is_capable"] is False

    def test_empty_measurements(self):
        svc = QualitySpcService([], lsl=9.0, usl=11.0)
        result = svc.capability_indices()
        assert result["cp"] is None
        assert result["is_capable"] is False
        assert result["sample_size"] == 0

    def test_zero_std_dev(self):
        svc = QualitySpcService([10.0, 10.0, 10.0], lsl=9.0, usl=11.0)
        result = svc.capability_indices()
        assert result["cp"] is None
        assert result["is_capable"] is True  # all within spec


class TestControlChart:

    def test_chart_with_data(self):
        measurements = [10.0, 10.1, 9.9, 10.0, 10.05]
        svc = QualitySpcService(measurements, lsl=9.0, usl=11.0)
        chart = svc.control_chart_data()
        assert chart["mean"] is not None
        assert chart["ucl"] is not None
        assert chart["lcl"] is not None
        assert len(chart["points"]) == 5
        assert chart["ucl"] > chart["mean"] > chart["lcl"]

    def test_chart_ooc_detection(self):
        # Many stable points + one outlier so outlier exceeds 3-sigma
        measurements = [10.0] * 20 + [50.0]
        svc = QualitySpcService(measurements, lsl=9.0, usl=11.0)
        chart = svc.control_chart_data()
        ooc_points = [p for p in chart["points"] if p["out_of_control"]]
        assert len(ooc_points) >= 1
        assert ooc_points[0]["index"] == 20

    def test_chart_empty(self):
        svc = QualitySpcService([], lsl=9.0, usl=11.0)
        chart = svc.control_chart_data()
        assert chart["mean"] is None
        assert chart["points"] == []


class TestOutOfControlIndices:

    def test_returns_indices(self):
        measurements = [10.0] * 20 + [50.0]
        svc = QualitySpcService(measurements, lsl=9.0, usl=11.0)
        indices = svc.out_of_control_indices()
        assert 20 in indices


class TestFromChecks:

    def test_factory_builds_from_checks(self):
        checks = [
            SimpleNamespace(measure_value=10.0),
            SimpleNamespace(measure_value=10.1),
            SimpleNamespace(measure_value=9.9),
            SimpleNamespace(measure_value=None),  # skipped
        ]
        point = SimpleNamespace(measure_min=9.0, measure_max=11.0)
        svc = QualitySpcService.from_checks(checks, point)
        result = svc.capability_indices()
        assert result["sample_size"] == 3

    def test_factory_with_no_thresholds(self):
        checks = [SimpleNamespace(measure_value=10.0)]
        point = SimpleNamespace(measure_min=None, measure_max=None)
        svc = QualitySpcService.from_checks(checks, point)
        result = svc.capability_indices()
        assert result["sample_size"] == 1
