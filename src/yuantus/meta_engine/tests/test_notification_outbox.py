from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.notifications.adapter import (
    NotificationAdapterConfigError,
    NotificationSendResult,
    NullNotificationAdapter,
    resolve_notification_adapter,
)
from yuantus.meta_engine.notifications.models import (
    NotificationDelivery,
    NotificationDeliveryReason,
    NotificationDeliveryState,
    NotificationOutbox,
)
from yuantus.meta_engine.notifications.service import NotificationOutboxService
from yuantus.meta_engine.notifications.worker import NotificationOutboxWorker
from yuantus.meta_engine.services.notification_service import NotificationService
from yuantus.models import user as _user  # noqa: F401
from yuantus.models.base import Base

import_all_models()

_PAST = datetime(2000, 1, 1, tzinfo=timezone.utc)
_FUTURE = datetime(2999, 1, 1, tzinfo=timezone.utc)


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'notification.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    yield db
    db.close()


class _FailingAdapter(NullNotificationAdapter):
    def __init__(self, reason: str = "remote_error"):
        self.reason = reason

    def send(self, delivery):
        return NotificationSendResult(
            ok=False,
            reason=self.reason,
            error_message="send failed",
        )


def test_notify_enqueues_durable_outbox_and_delivery(session):
    NotificationService(session).notify(
        "eco.stage.changed",
        {"eco_id": "ECO-1", "stage": "review"},
        recipients=["qa@example.test"],
    )
    session.commit()

    outbox = session.query(NotificationOutbox).one()
    delivery = session.query(NotificationDelivery).one()
    assert outbox.event_type == "eco.stage.changed"
    assert outbox.payload == {"eco_id": "ECO-1", "stage": "review"}
    assert delivery.notification_id == outbox.id
    assert delivery.recipient_email == "qa@example.test"
    assert delivery.state == NotificationDeliveryState.PENDING.value


def test_notify_is_idempotent_for_same_event_payload_and_recipients(session):
    svc = NotificationService(session)
    for _ in range(2):
        svc.notify("eco.stage.changed", {"eco_id": "ECO-1"}, recipients=["qa@example.test"])
    session.commit()

    assert session.query(NotificationOutbox).count() == 1
    assert session.query(NotificationDelivery).count() == 1


def test_explicit_idempotency_key_reuse_with_changed_payload_is_rejected(session):
    svc = NotificationOutboxService(session)
    svc.enqueue(
        event="eco.stage.changed",
        payload={"eco_id": "ECO-1"},
        recipients=["qa@example.test"],
        idempotency_key="key-1",
    )

    with pytest.raises(ValueError, match="idempotency key"):
        svc.enqueue(
            event="eco.stage.changed",
            payload={"eco_id": "ECO-2"},
            recipients=["qa@example.test"],
            idempotency_key="key-1",
        )


def test_missing_email_delivery_is_terminal_failed_not_crash(session):
    NotificationService(session).notify(
        "eco.stage.changed",
        {"eco_id": "ECO-1"},
        recipients=["stage-approver-role"],
    )
    session.commit()

    delivery = session.query(NotificationDelivery).one()
    assert delivery.state == NotificationDeliveryState.FAILED.value
    assert delivery.reason == NotificationDeliveryReason.RECIPIENT_MISSING.value
    assert NotificationOutboxWorker("w1").run_once_with_session(session) == 0


def test_worker_sends_pending_delivery_via_null_adapter(session):
    NotificationService(session).notify(
        "eco.stage.changed",
        {"eco_id": "ECO-1"},
        recipients=["qa@example.test"],
    )
    delivery = session.query(NotificationDelivery).one()
    delivery.next_attempt_at = _PAST
    session.commit()

    processed = NotificationOutboxWorker(
        "w1", adapter=NullNotificationAdapter()
    ).run_once_with_session(session)

    session.refresh(delivery)
    assert processed == 1
    assert delivery.state == NotificationDeliveryState.SENT.value
    assert delivery.reason is None
    assert delivery.remote_id == f"null:{delivery.id}"
    assert delivery.sent_at is not None


def test_smtp_adapter_requires_explicit_host_and_from():
    settings = SimpleNamespace(
        NOTIFICATION_EMAIL_ADAPTER="smtp",
        NOTIFICATION_SMTP_HOST="",
        NOTIFICATION_SMTP_PORT=25,
        NOTIFICATION_SMTP_FROM="",
        NOTIFICATION_SMTP_TIMEOUT_SECONDS=10,
    )
    with pytest.raises(NotificationAdapterConfigError):
        resolve_notification_adapter(settings)


def test_retryable_failure_reschedules_then_dead_letters(session):
    NotificationService(session).notify(
        "eco.stage.changed",
        {"eco_id": "ECO-1"},
        recipients=["qa@example.test"],
    )
    delivery = session.query(NotificationDelivery).one()
    delivery.max_attempts = 2
    delivery.next_attempt_at = _PAST
    session.commit()

    worker = NotificationOutboxWorker(
        "w1", adapter=_FailingAdapter(), backoff_seconds=1
    )
    assert worker.run_once_with_session(session) == 1
    session.refresh(delivery)
    assert delivery.state == NotificationDeliveryState.PENDING.value
    assert delivery.reason == NotificationDeliveryReason.REMOTE_ERROR.value
    assert delivery.attempt_count == 1

    delivery.next_attempt_at = _PAST
    session.commit()
    assert worker.run_once_with_session(session) == 1
    session.refresh(delivery)
    assert delivery.state == NotificationDeliveryState.FAILED.value
    assert delivery.reason == NotificationDeliveryReason.REMOTE_ERROR.value
    assert delivery.attempt_count == 2


def test_claim_batch_skips_future_rows_and_reclaims_stale(session):
    NotificationService(session).notify(
        "eco.stage.changed",
        {"eco_id": "ECO-1"},
        recipients=["future@example.test", "stale@example.test"],
    )
    rows = session.query(NotificationDelivery).order_by(NotificationDelivery.recipient_key).all()
    future, stale = rows
    future.next_attempt_at = _FUTURE
    stale.next_attempt_at = _PAST
    stale.worker_id = "dead-worker"
    stale.claimed_at = datetime.now(timezone.utc) - timedelta(hours=2)
    session.commit()

    worker = NotificationOutboxWorker(
        "w1", adapter=NullNotificationAdapter(), stale_timeout_seconds=1
    )
    assert worker._reclaim_stale(session) == 1
    claimed = worker._claim_batch(session)

    assert [row.id for row in claimed] == [stale.id]
    session.refresh(stale)
    assert stale.worker_id == "w1"
    assert stale.claimed_at is not None
