from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from yuantus.context import org_id_var, tenant_id_var, user_id_var
from yuantus.meta_engine.notifications.models import (
    NotificationDelivery,
    NotificationDeliveryReason,
    NotificationDeliveryState,
    NotificationOutbox,
    NotificationOutboxState,
)
from yuantus.security.rbac.models import RBACUser


def _json_default(value: Any) -> str:
    return str(value)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_recipients(recipients: Iterable[Any] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in recipients or []:
        key = _clean(raw)
        if key is None or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


class NotificationOutboxService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        event: str,
        payload: Mapping[str, Any] | None = None,
        recipients: Sequence[Any] | None = None,
        tenant_id: str | None = None,
        org_id: str | None = None,
        created_by_id: int | None = None,
        title: str | None = None,
        body: str | None = None,
        object_type: str | None = None,
        object_id: str | None = None,
        channel: str = "email",
        max_attempts: int = 3,
        idempotency_key: str | None = None,
        properties: Mapping[str, Any] | None = None,
    ) -> NotificationOutbox:
        tenant = _clean(tenant_id) or _clean(tenant_id_var.get())
        org = _clean(org_id) or _clean(org_id_var.get())
        creator = created_by_id
        if creator is None:
            raw_user_id = _clean(user_id_var.get())
            if raw_user_id and raw_user_id.isdigit():
                creator = int(raw_user_id)

        payload_snapshot: dict[str, Any] = dict(payload or {})
        recipient_keys = _normalize_recipients(recipients)
        fingerprint_input = {
            "tenant_id": tenant,
            "org_id": org,
            "event": event,
            "object_type": object_type,
            "object_id": object_id,
            "title": title,
            "body": body,
            "payload": payload_snapshot,
            "recipients": recipient_keys,
            "channel": channel,
        }
        payload_fingerprint = _fingerprint(fingerprint_input)
        idem = _clean(idempotency_key) or payload_fingerprint

        existing = (
            self.session.query(NotificationOutbox)
            .filter(NotificationOutbox.idempotency_key == idem)
            .one_or_none()
        )
        if existing is not None:
            if existing.payload_fingerprint != payload_fingerprint:
                raise ValueError("notification idempotency key reused with different payload")
            return existing

        outbox = NotificationOutbox(
            id=str(uuid.uuid4()),
            tenant_id=tenant,
            org_id=org,
            event_type=str(event),
            object_type=_clean(object_type),
            object_id=_clean(object_id),
            title=_clean(title),
            body=body,
            payload=payload_snapshot,
            payload_fingerprint=payload_fingerprint,
            idempotency_key=idem,
            state=NotificationOutboxState.READY.value,
            properties=dict(properties or {}),
            created_by_id=creator,
        )
        self.session.add(outbox)
        self.session.flush()

        for recipient_key in recipient_keys:
            self.session.add(
                self._build_delivery(
                    outbox=outbox,
                    recipient_key=recipient_key,
                    channel=channel,
                    max_attempts=max_attempts,
                )
            )
        return outbox

    def _build_delivery(
        self,
        *,
        outbox: NotificationOutbox,
        recipient_key: str,
        channel: str,
        max_attempts: int,
    ) -> NotificationDelivery:
        user_id: int | None = int(recipient_key) if recipient_key.isdigit() else None
        email: str | None = recipient_key if "@" in recipient_key else None
        if user_id is not None:
            user = self.session.get(RBACUser, user_id)
            if user is not None:
                email = _clean(user.email)

        state = NotificationDeliveryState.PENDING.value
        reason = None
        if not email:
            state = NotificationDeliveryState.FAILED.value
            reason = NotificationDeliveryReason.RECIPIENT_MISSING.value

        return NotificationDelivery(
            id=str(uuid.uuid4()),
            notification_id=outbox.id,
            tenant_id=outbox.tenant_id,
            org_id=outbox.org_id,
            recipient_user_id=user_id,
            recipient_key=recipient_key,
            recipient_email=email,
            channel=channel,
            state=state,
            reason=reason,
            max_attempts=max(1, int(max_attempts or 1)),
            payload={
                "event": outbox.event_type,
                "title": outbox.title,
                "body": outbox.body,
                "payload": outbox.payload or {},
            },
            properties={},
        )
