from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable

from yuantus.database import get_db_session
from yuantus.meta_engine.events.domain_events import (
    EcoCreatedEvent,
    EcoDeletedEvent,
    EcoUpdatedEvent,
    ItemCreatedEvent,
    ItemDeletedEvent,
    ItemStateChangedEvent,
    ItemUpdatedEvent,
)
from yuantus.meta_engine.events.event_bus import event_bus
from yuantus.meta_engine.models.eco import ECO
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.search_service import SearchService

logger = logging.getLogger(__name__)

_INDEX_READY = False
_INDEX_LOCK = Lock()
_ECO_INDEX_READY = False
_ECO_INDEX_LOCK = Lock()
_REGISTERED = False
_REGISTER_LOCK = Lock()
_STATUS_LOCK = Lock()
_EVENT_TYPES = {
    ItemCreatedEvent: "item.created",
    ItemUpdatedEvent: "item.updated",
    ItemStateChangedEvent: "item.state_changed",
    ItemDeletedEvent: "item.deleted",
    EcoCreatedEvent: "eco.created",
    EcoUpdatedEvent: "eco.updated",
    EcoDeletedEvent: "eco.deleted",
}
_EVENT_COUNTS = {event_type: 0 for event_type in _EVENT_TYPES.values()}
_SUCCESS_COUNTS = {event_type: 0 for event_type in _EVENT_TYPES.values()}
_SKIPPED_COUNTS = {event_type: 0 for event_type in _EVENT_TYPES.values()}
_ERROR_COUNTS = {event_type: 0 for event_type in _EVENT_TYPES.values()}
_LAST_EVENT_TYPE: str | None = None
_LAST_EVENT_AT: str | None = None
_LAST_OUTCOME: str | None = None
_LAST_SUCCESS_EVENT_TYPE: str | None = None
_LAST_SUCCESS_AT: str | None = None
_LAST_SKIPPED_EVENT_TYPE: str | None = None
_LAST_SKIPPED_AT: str | None = None
_LAST_SKIPPED_REASON: str | None = None
_LAST_ERROR_EVENT_TYPE: str | None = None
_LAST_ERROR_AT: str | None = None
_LAST_ERROR: str | None = None
_MAX_ERROR_MESSAGE_LENGTH = 300
_SENSITIVE_ERROR_PATTERNS = (
    (
        re.compile(
            r"(?i)"
            r"(password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key)"
            r"(\s*[=:]\s*)"
            r"([^,\s;&]+)"
        ),
        r"\1\2***",
    ),
    (re.compile(r"://([^:/\s]+):([^@\s]+)@"), r"://\1:***@"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_event_received(event_type: str) -> None:
    global _LAST_EVENT_TYPE, _LAST_EVENT_AT
    with _STATUS_LOCK:
        _EVENT_COUNTS[event_type] = _EVENT_COUNTS.get(event_type, 0) + 1
        _LAST_EVENT_TYPE = event_type
        _LAST_EVENT_AT = _utc_now()


def _record_event_success(event_type: str) -> None:
    global _LAST_OUTCOME, _LAST_SUCCESS_EVENT_TYPE, _LAST_SUCCESS_AT
    with _STATUS_LOCK:
        _SUCCESS_COUNTS[event_type] = _SUCCESS_COUNTS.get(event_type, 0) + 1
        _LAST_OUTCOME = "success"
        _LAST_SUCCESS_EVENT_TYPE = event_type
        _LAST_SUCCESS_AT = _utc_now()


def _record_event_skipped(event_type: str, reason: str) -> None:
    global _LAST_OUTCOME, _LAST_SKIPPED_EVENT_TYPE, _LAST_SKIPPED_AT, _LAST_SKIPPED_REASON
    with _STATUS_LOCK:
        _SKIPPED_COUNTS[event_type] = _SKIPPED_COUNTS.get(event_type, 0) + 1
        _LAST_OUTCOME = "skipped"
        _LAST_SKIPPED_EVENT_TYPE = event_type
        _LAST_SKIPPED_AT = _utc_now()
        _LAST_SKIPPED_REASON = reason


def _record_event_error(event_type: str, exc: Exception) -> None:
    global _LAST_OUTCOME, _LAST_ERROR_EVENT_TYPE, _LAST_ERROR_AT, _LAST_ERROR
    with _STATUS_LOCK:
        _ERROR_COUNTS[event_type] = _ERROR_COUNTS.get(event_type, 0) + 1
        _LAST_OUTCOME = "error"
        _LAST_ERROR_EVENT_TYPE = event_type
        _LAST_ERROR_AT = _utc_now()
        _LAST_ERROR = _format_error(exc)


def _format_error(exc: Exception) -> str:
    message = str(exc).strip()
    for pattern, replacement in _SENSITIVE_ERROR_PATTERNS:
        message = pattern.sub(replacement, message)
    if len(message) > _MAX_ERROR_MESSAGE_LENGTH:
        message = f"{message[:_MAX_ERROR_MESSAGE_LENGTH]}..."
    if not message:
        return type(exc).__name__
    return f"{type(exc).__name__}: {message}"


def indexer_status() -> dict[str, Any]:
    subscription_counts = _subscription_counts()
    with _STATUS_LOCK:
        return {
            "registered": _REGISTERED,
            "item_index_ready": _INDEX_READY,
            "eco_index_ready": _ECO_INDEX_READY,
            "handlers": list(_EVENT_TYPES.values()),
            "subscription_counts": subscription_counts,
            "missing_handlers": [
                event_type
                for event_type, count in subscription_counts.items()
                if count == 0
            ],
            "event_counts": dict(_EVENT_COUNTS),
            "success_counts": dict(_SUCCESS_COUNTS),
            "skipped_counts": dict(_SKIPPED_COUNTS),
            "error_counts": dict(_ERROR_COUNTS),
            "last_event_type": _LAST_EVENT_TYPE,
            "last_event_at": _LAST_EVENT_AT,
            "last_outcome": _LAST_OUTCOME,
            "last_success_event_type": _LAST_SUCCESS_EVENT_TYPE,
            "last_success_at": _LAST_SUCCESS_AT,
            "last_skipped_event_type": _LAST_SKIPPED_EVENT_TYPE,
            "last_skipped_at": _LAST_SKIPPED_AT,
            "last_skipped_reason": _LAST_SKIPPED_REASON,
            "last_error_event_type": _LAST_ERROR_EVENT_TYPE,
            "last_error_at": _LAST_ERROR_AT,
            "last_error": _LAST_ERROR,
        }


def _ensure_index(service: SearchService) -> None:
    global _INDEX_READY
    if _INDEX_READY or not service.client:
        return
    with _INDEX_LOCK:
        if _INDEX_READY:
            return
        try:
            service.ensure_index()
            _INDEX_READY = True
        except Exception:
            logger.exception("Search index initialization failed")


def _ensure_eco_index(service: SearchService) -> None:
    global _ECO_INDEX_READY
    if _ECO_INDEX_READY or not service.client:
        return
    with _ECO_INDEX_LOCK:
        if _ECO_INDEX_READY:
            return
        try:
            service.ensure_eco_index()
            _ECO_INDEX_READY = True
        except Exception:
            logger.exception("ECO search index initialization failed")


def _with_search_service(
    event_type: str, handler: Callable[[SearchService], None]
) -> None:
    try:
        with get_db_session() as session:
            service = SearchService(session)
            if not service.client:
                _record_event_skipped(event_type, "search-engine-disabled")
                return
            _ensure_index(service)
            handler(service)
            _record_event_success(event_type)
    except Exception as exc:
        _record_event_error(event_type, exc)
        logger.exception("Search indexing handler failed")


def _handle_item_created(event: ItemCreatedEvent) -> None:
    _record_event_received(event.event_type)

    def _index(service: SearchService) -> None:
        item = service.session.get(Item, event.item_id) if service.session else None
        if not item:
            logger.debug("Search index skip (item missing): %s", event.item_id)
            return
        service.index_item(item)

    _with_search_service(event.event_type, _index)


def _handle_item_updated(event: ItemUpdatedEvent) -> None:
    _record_event_received(event.event_type)

    def _index(service: SearchService) -> None:
        item = service.session.get(Item, event.item_id) if service.session else None
        if not item:
            logger.debug("Search index skip (item missing): %s", event.item_id)
            return
        service.index_item(item)

    _with_search_service(event.event_type, _index)


def _handle_item_deleted(event: ItemDeletedEvent) -> None:
    _record_event_received(event.event_type)

    def _delete(service: SearchService) -> None:
        service.delete_item(event.item_id)

    _with_search_service(event.event_type, _delete)


def _handle_item_state_changed(event: ItemStateChangedEvent) -> None:
    _record_event_received(event.event_type)

    def _index(service: SearchService) -> None:
        item = service.session.get(Item, event.item_id) if service.session else None
        if not item:
            logger.debug("Search index skip (item missing): %s", event.item_id)
            return
        service.index_item(item)

    _with_search_service(event.event_type, _index)


def _handle_eco_created(event: EcoCreatedEvent) -> None:
    _record_event_received(event.event_type)

    def _index(service: SearchService) -> None:
        _ensure_eco_index(service)
        eco = service.session.get(ECO, event.eco_id) if service.session else None
        if not eco:
            logger.debug("ECO index skip (eco missing): %s", event.eco_id)
            return
        service.index_eco(eco)

    _with_search_service(event.event_type, _index)


def _handle_eco_updated(event: EcoUpdatedEvent) -> None:
    _record_event_received(event.event_type)

    def _index(service: SearchService) -> None:
        _ensure_eco_index(service)
        eco = service.session.get(ECO, event.eco_id) if service.session else None
        if not eco:
            logger.debug("ECO index skip (eco missing): %s", event.eco_id)
            return
        service.index_eco(eco)

    _with_search_service(event.event_type, _index)


def _handle_eco_deleted(event: EcoDeletedEvent) -> None:
    _record_event_received(event.event_type)

    def _delete(service: SearchService) -> None:
        _ensure_eco_index(service)
        service.delete_eco(event.eco_id)

    _with_search_service(event.event_type, _delete)


_HANDLERS_BY_EVENT = {
    ItemCreatedEvent: _handle_item_created,
    ItemUpdatedEvent: _handle_item_updated,
    ItemStateChangedEvent: _handle_item_state_changed,
    ItemDeletedEvent: _handle_item_deleted,
    EcoCreatedEvent: _handle_eco_created,
    EcoUpdatedEvent: _handle_eco_updated,
    EcoDeletedEvent: _handle_eco_deleted,
}


def _subscription_counts() -> dict[str, int]:
    subscribers = getattr(event_bus, "_subscribers", {})
    return {
        _EVENT_TYPES[event_type]: sum(
            1 for handler in subscribers.get(event_type, []) if handler is expected
        )
        for event_type, expected in _HANDLERS_BY_EVENT.items()
    }


def register_search_index_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    with _REGISTER_LOCK:
        if _REGISTERED:
            return
        for event_type, handler in _HANDLERS_BY_EVENT.items():
            event_bus.subscribe(event_type, handler)
        _REGISTERED = True
        logger.info("Search index handlers registered")
