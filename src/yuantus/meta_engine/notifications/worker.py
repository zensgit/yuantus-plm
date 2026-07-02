from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import asc, or_
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.database import get_db_session
from yuantus.meta_engine.notifications.adapter import (
    NotificationAdapter,
    NotificationAdapterConfigError,
    NotificationSendResult,
    resolve_notification_adapter,
)
from yuantus.meta_engine.notifications.models import (
    NotificationDelivery,
    NotificationDeliveryReason,
    NotificationDeliveryState,
)

logger = logging.getLogger(__name__)

_RETRYABLE = {
    NotificationDeliveryReason.ADAPTER_ERROR.value,
    NotificationDeliveryReason.REMOTE_ERROR.value,
}


class NotificationOutboxWorker:
    def __init__(
        self,
        worker_id: str,
        *,
        adapter: Optional[NotificationAdapter] = None,
        batch_size: Optional[int] = None,
        backoff_seconds: Optional[int] = None,
        stale_timeout_seconds: Optional[int] = None,
        poll_interval_seconds: Optional[int] = None,
    ) -> None:
        s = get_settings()
        self.worker_id = worker_id
        self.adapter = adapter
        self.batch_size = (
            batch_size if batch_size is not None else s.NOTIFICATION_OUTBOX_BATCH_SIZE
        )
        self.backoff_seconds = (
            backoff_seconds
            if backoff_seconds is not None
            else s.NOTIFICATION_OUTBOX_RETRY_BACKOFF_SECONDS
        )
        self.stale_timeout_seconds = (
            stale_timeout_seconds
            if stale_timeout_seconds is not None
            else s.NOTIFICATION_OUTBOX_STALE_TIMEOUT_SECONDS
        )
        self.poll_interval_seconds = (
            poll_interval_seconds
            if poll_interval_seconds is not None
            else s.NOTIFICATION_OUTBOX_POLL_INTERVAL_SECONDS
        )
        self._running = False

    def run_once(self) -> int:
        with get_db_session() as session:
            return self.run_once_with_session(session)

    def run_once_with_session(self, session: Session) -> int:
        self._reclaim_stale(session)
        rows = self._claim_batch(session)
        for row in rows:
            self._process_row(session, row)
        return len(rows)

    def _reclaim_stale(self, session: Session) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.stale_timeout_seconds)
        rows = (
            session.query(NotificationDelivery)
            .filter(
                NotificationDelivery.state == NotificationDeliveryState.PENDING.value,
                NotificationDelivery.worker_id.isnot(None),
                NotificationDelivery.claimed_at.isnot(None),
                NotificationDelivery.claimed_at < cutoff,
            )
            .all()
        )
        for row in rows:
            row.worker_id = None
            row.claimed_at = None
        if rows:
            session.commit()
            logger.warning(
                "notification-worker '%s' reclaimed %d stale row(s)",
                self.worker_id,
                len(rows),
            )
        return len(rows)

    def _claim_batch(self, session: Session) -> List[NotificationDelivery]:
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(seconds=self.stale_timeout_seconds)
        dialect = session.bind.dialect.name if session.bind else "unknown"
        query = (
            session.query(NotificationDelivery)
            .filter(
                NotificationDelivery.state == NotificationDeliveryState.PENDING.value,
                NotificationDelivery.next_attempt_at <= now,
                or_(
                    NotificationDelivery.claimed_at.is_(None),
                    NotificationDelivery.claimed_at < stale_cutoff,
                ),
            )
            .order_by(
                asc(NotificationDelivery.next_attempt_at),
                asc(NotificationDelivery.created_at),
            )
        )
        if dialect == "postgresql":
            query = query.with_for_update(skip_locked=True)
        rows = query.limit(self.batch_size).all()
        for row in rows:
            row.worker_id = self.worker_id
            row.claimed_at = now
        if rows:
            session.commit()
        return rows

    def _adapter(self) -> NotificationAdapter:
        if self.adapter is not None:
            return self.adapter
        return resolve_notification_adapter(get_settings())

    def _process_row(self, session: Session, row: NotificationDelivery) -> None:
        if not row.recipient_email:
            row.state = NotificationDeliveryState.FAILED.value
            row.reason = NotificationDeliveryReason.RECIPIENT_MISSING.value
            row.error_message = "recipient email is missing"
            row.worker_id = None
            row.claimed_at = None
            session.commit()
            return

        try:
            result = self._adapter().send(row)
        except NotificationAdapterConfigError as exc:
            result = NotificationSendResult(
                ok=False,
                reason=NotificationDeliveryReason.ADAPTER_ERROR.value,
                error_message=str(exc),
            )
        except Exception as exc:
            result = NotificationSendResult(
                ok=False,
                reason=NotificationDeliveryReason.ADAPTER_ERROR.value,
                error_message=str(exc),
            )

        row.attempt_count = (row.attempt_count or 0) + 1
        row.worker_id = None
        row.claimed_at = None
        row.properties = {**(row.properties or {}), **dict(result.properties or {})}
        if result.ok:
            row.state = NotificationDeliveryState.SENT.value
            row.reason = None
            row.remote_id = result.remote_id
            row.error_message = None
            row.sent_at = datetime.now(timezone.utc)
            session.commit()
            return

        reason = result.reason or NotificationDeliveryReason.REMOTE_ERROR.value
        row.reason = reason
        row.error_message = result.error_message
        if reason in _RETRYABLE and (row.attempt_count or 0) < (row.max_attempts or 1):
            row.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=max(1, self.backoff_seconds)
            )
        else:
            row.state = NotificationDeliveryState.FAILED.value
        session.commit()

    def run_forever(self) -> None:
        self._running = True
        logger.info("notification-worker '%s' started", self.worker_id)
        while self._running:
            try:
                self.run_once()
            except Exception as exc:
                logger.error(
                    "notification-worker '%s' tick error: %s",
                    self.worker_id,
                    exc,
                    exc_info=True,
                )
            time.sleep(self.poll_interval_seconds)

    def stop(self) -> None:
        self._running = False

