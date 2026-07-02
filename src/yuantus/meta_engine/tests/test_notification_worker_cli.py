"""Notification worker CLI entrypoint (`yuantus notification-worker`)."""
from __future__ import annotations

import pathlib

from typer.testing import CliRunner

import yuantus.cli as cli_mod
from yuantus.cli import app
from yuantus.meta_engine.notifications.worker import NotificationOutboxWorker

runner = CliRunner()
_CLI_TEXT = pathlib.Path(cli_mod.__file__).read_text(encoding="utf-8")


def test_command_is_registered_and_wired():
    assert '@app.command(name="notification-worker")' in _CLI_TEXT
    assert "NotificationOutboxWorker(" in _CLI_TEXT
    assert "w.run_once()" in _CLI_TEXT and "w.run_forever()" in _CLI_TEXT
    assert '"--tenant"' in _CLI_TEXT and '"--org"' in _CLI_TEXT
    assert "once:" in _CLI_TEXT


def test_once_drains_one_batch_and_reports(monkeypatch):
    monkeypatch.setattr(NotificationOutboxWorker, "run_once", lambda self: 3)
    result = runner.invoke(app, ["notification-worker", "--once"])
    assert result.exit_code == 0
    assert "Processed 3 notification delivery row(s)." in result.output


def test_forever_is_used_when_not_once(monkeypatch):
    ran = {}

    def _forever(self):
        ran["forever"] = True

    def _no_run_once(self):
        raise AssertionError("run_once must not be called in daemon mode")

    monkeypatch.setattr(NotificationOutboxWorker, "run_forever", _forever)
    monkeypatch.setattr(NotificationOutboxWorker, "run_once", _no_run_once)
    result = runner.invoke(app, ["notification-worker"])
    assert result.exit_code == 0
    assert ran.get("forever") is True


def test_default_and_custom_worker_id(monkeypatch):
    seen = {}

    def _capture(self):
        seen["wid"] = self.worker_id
        return 0

    monkeypatch.setattr(NotificationOutboxWorker, "run_once", _capture)

    runner.invoke(app, ["notification-worker", "--once"])
    assert seen["wid"] == "notification-worker-1"

    runner.invoke(app, ["notification-worker", "--once", "--worker-id", "ops-7"])
    assert seen["wid"] == "ops-7"


def test_keyboard_interrupt_stops_cleanly(monkeypatch):
    stopped = {}

    def _forever(self):
        raise KeyboardInterrupt

    def _stop(self):
        stopped["stopped"] = True

    monkeypatch.setattr(NotificationOutboxWorker, "run_forever", _forever)
    monkeypatch.setattr(NotificationOutboxWorker, "stop", _stop)
    result = runner.invoke(app, ["notification-worker"])
    assert result.exit_code == 0
    assert stopped.get("stopped") is True

