"""Durable notification enqueue surface for workflow events."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from yuantus.meta_engine.notifications.service import NotificationOutboxService


class NotificationService:
    def __init__(self, session: Session):
        self.session = session

    def notify(
        self,
        event: str,
        payload: Dict[str, Any],
        recipients: Optional[List[str]] = None,
    ) -> None:
        NotificationOutboxService(self.session).enqueue(
            event=event,
            payload=payload,
            recipients=recipients or [],
        )
