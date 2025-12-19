"""
Transactional event publishing helpers.

Collect domain events on the current SQLAlchemy Session and publish them only
after the surrounding transaction successfully commits.
"""

from __future__ import annotations

from threading import Lock
from typing import List

from sqlalchemy import event
from sqlalchemy.orm import Session

from yuantus.meta_engine.events.domain_events import DomainEvent
from yuantus.meta_engine.events.event_bus import event_bus

_PENDING_EVENTS_KEY = "meta_engine_pending_events"
_REGISTER_LOCK = Lock()
_REGISTERED = False


def enqueue_event(session: Session, domain_event: DomainEvent) -> None:
    """
    Enqueue a DomainEvent on the given Session.

    The event will be published via the in-memory EventBus only after the
    session commits successfully.
    """
    _ensure_session_hooks()
    pending: List[DomainEvent] = session.info.setdefault(_PENDING_EVENTS_KEY, [])
    pending.append(domain_event)


def _ensure_session_hooks() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    with _REGISTER_LOCK:
        if _REGISTERED:
            return
        event.listen(Session, "after_commit", _after_commit)
        event.listen(Session, "after_soft_rollback", _after_rollback)
        _REGISTERED = True


def _after_commit(session: Session) -> None:
    pending: List[DomainEvent] = session.info.pop(_PENDING_EVENTS_KEY, [])
    for domain_event in pending:
        event_bus.publish(domain_event)


def _after_rollback(session: Session, previous_transaction) -> None:  # type: ignore[no-untyped-def]
    # Drop any queued events if the transaction rolls back.
    session.info.pop(_PENDING_EVENTS_KEY, None)
