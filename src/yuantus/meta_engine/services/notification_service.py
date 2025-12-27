"""
Notification Service
Lightweight notification dispatcher for workflow events.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session


class NotificationService:
    def __init__(self, session: Session):
        self.session = session

    def notify(
        self,
        event: str,
        payload: Dict[str, Any],
        recipients: Optional[List[str]] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "recipients": recipients or [],
            "payload": payload,
        }

        import logging

        logger = logging.getLogger("plm_notify")
        logger.info(f"[NOTIFY] {entry}")
