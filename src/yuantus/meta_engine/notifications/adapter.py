from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class NotificationSendResult:
    ok: bool
    reason: str | None = None
    error_message: str | None = None
    remote_id: str | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)


class NotificationAdapter(Protocol):
    def send(self, delivery: Any) -> NotificationSendResult: ...


class NotificationAdapterConfigError(RuntimeError):
    pass


class NullNotificationAdapter:
    """No-I/O adapter for deterministic tests and unconfigured deployments."""

    def send(self, delivery: Any) -> NotificationSendResult:
        return NotificationSendResult(
            ok=True,
            remote_id=f"null:{delivery.id}",
            properties={"adapter": "null"},
        )


class SmtpNotificationAdapter:
    """Small SMTP adapter, selected only by explicit configuration."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        timeout_seconds: int = 10,
    ) -> None:
        if not host.strip() or not sender.strip():
            raise NotificationAdapterConfigError(
                "SMTP notification adapter requires host and sender"
            )
        self.host = host.strip()
        self.port = int(port)
        self.sender = sender.strip()
        self.timeout_seconds = int(timeout_seconds)

    def send(self, delivery: Any) -> NotificationSendResult:
        if not delivery.recipient_email:
            return NotificationSendResult(
                ok=False,
                reason="recipient_missing",
                error_message="recipient email is missing",
            )

        payload = delivery.payload or {}
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = delivery.recipient_email
        msg["Subject"] = str(payload.get("title") or "Yuantus notification")
        msg.set_content(str(payload.get("body") or ""))

        try:
            with smtplib.SMTP(
                self.host, self.port, timeout=self.timeout_seconds
            ) as smtp:
                smtp.send_message(msg)
        except Exception as exc:  # pragma: no cover - exercised with real SMTP config
            return NotificationSendResult(
                ok=False,
                reason="remote_error",
                error_message=str(exc),
            )
        return NotificationSendResult(
            ok=True,
            remote_id=f"smtp:{delivery.id}",
            properties={"adapter": "smtp"},
        )


def resolve_notification_adapter(settings: Any) -> NotificationAdapter:
    adapter = str(getattr(settings, "NOTIFICATION_EMAIL_ADAPTER", "null") or "null")
    adapter = adapter.strip().lower()
    if adapter in {"", "null"}:
        return NullNotificationAdapter()
    if adapter == "smtp":
        return SmtpNotificationAdapter(
            host=str(getattr(settings, "NOTIFICATION_SMTP_HOST", "") or ""),
            port=int(getattr(settings, "NOTIFICATION_SMTP_PORT", 25) or 25),
            sender=str(getattr(settings, "NOTIFICATION_SMTP_FROM", "") or ""),
            timeout_seconds=int(
                getattr(settings, "NOTIFICATION_SMTP_TIMEOUT_SECONDS", 10) or 10
            ),
        )
    raise NotificationAdapterConfigError(f"unknown notification adapter: {adapter}")

