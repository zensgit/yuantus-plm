"""Tests for C16 – QualityAnalyticsService."""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from yuantus.meta_engine.quality.analytics_service import QualityAnalyticsService


def _point(id="pt-1", name="Torque Check"):
    return SimpleNamespace(id=id, name=name)


def _check(id="chk-1", point_id="pt-1", result="pass"):
    return SimpleNamespace(id=id, point_id=point_id, result=result)


def _alert(id="alt-1", state="new", check_id="chk-1", priority="medium", created_at=None):
    return SimpleNamespace(
        id=id,
        state=state,
        check_id=check_id,
        priority=priority,
        created_at=created_at or datetime(2026, 3, 1),
    )


class TestDefectRateByPoint:

    def test_single_point(self):
        checks = [
            _check(id="c1", result="pass"),
            _check(id="c2", result="fail"),
            _check(id="c3", result="pass"),
        ]
        svc = QualityAnalyticsService(checks=checks, points=[_point()])
        result = svc.defect_rate_by_point()
        assert len(result["points"]) == 1
        assert result["points"][0]["total_checks"] == 3
        assert result["points"][0]["fail_count"] == 1
        assert result["points"][0]["defect_rate"] == round(1 / 3, 4)

    def test_empty(self):
        svc = QualityAnalyticsService()
        result = svc.defect_rate_by_point()
        assert result["points"] == []


class TestCheckResultDistribution:

    def test_distribution(self):
        checks = [
            _check(result="pass"),
            _check(result="pass"),
            _check(result="fail"),
            _check(result="warning"),
        ]
        svc = QualityAnalyticsService(checks=checks)
        result = svc.check_result_distribution()
        assert result["total_checks"] == 4
        assert result["pass"] == 2
        assert result["fail"] == 1
        assert result["warning"] == 1
        assert result["pass_rate"] == 0.5

    def test_empty(self):
        svc = QualityAnalyticsService()
        result = svc.check_result_distribution()
        assert result["total_checks"] == 0


class TestAlertAging:

    def test_buckets(self):
        now = datetime(2026, 3, 10, 12, 0)
        alerts = [
            _alert(id="a1", state="new", created_at=now - timedelta(hours=12)),      # under 24h
            _alert(id="a2", state="confirmed", created_at=now - timedelta(hours=48)),  # 24h-72h
            _alert(id="a3", state="in_progress", created_at=now - timedelta(hours=100)),  # over 72h
            _alert(id="a4", state="closed", created_at=now - timedelta(hours=200)),   # closed, skip
        ]
        svc = QualityAnalyticsService(alerts=alerts)
        result = svc.alert_aging(now=now)
        assert result["under_24h"] == 1
        assert result["24h_to_72h"] == 1
        assert result["over_72h"] == 1
        assert result["total_open"] == 3

    def test_empty(self):
        svc = QualityAnalyticsService()
        result = svc.alert_aging()
        assert result["total_open"] == 0


class TestPointEffectiveness:

    def test_effectiveness(self):
        checks = [
            _check(id="c1", point_id="pt-1", result="fail"),
            _check(id="c2", point_id="pt-1", result="pass"),
            _check(id="c3", point_id="pt-1", result="fail"),
        ]
        alerts = [
            _alert(id="a1", check_id="c1"),
            _alert(id="a2", check_id="c3"),
        ]
        svc = QualityAnalyticsService(
            checks=checks, alerts=alerts, points=[_point()]
        )
        result = svc.point_effectiveness()
        assert len(result["points"]) == 1
        assert result["points"][0]["check_count"] == 3
        assert result["points"][0]["alert_count"] == 2
        assert result["points"][0]["checks_per_alert"] == 1.5


class TestFullAnalytics:

    def test_full_keys(self):
        svc = QualityAnalyticsService(
            checks=[_check()], alerts=[_alert()], points=[_point()]
        )
        result = svc.full_analytics()
        assert result["report"] == "quality-analytics"
        assert "generated_at" in result
        assert "defect_rates" in result
        assert "result_distribution" in result
        assert "alert_aging" in result
        assert "point_effectiveness" in result
