"""CAD-PDM C3 — date-BOM auto-obsolete polling worker (default-OFF).

Scan-based (no outbox table): each tick it scans expired date effectivities and runs the
idempotent ``DateEffectivityObsoleteService.process_expired`` for each, so re-scanning is
safe (already-Obsolete items skip promote; parent flags upsert). Mirrors the lifecycle of
``EcmPublicationOutboxWorker`` (``run_once`` / ``run_once_with_session`` / ``run_forever``).

Two gates, both must be on: the global kill-switch ``DATE_EFFECTIVITY_OBSOLETE_ENABLED``
(restart-only setting) and the per-tenant ``EntitlementService`` feature. Off by default → a
no-op, so landing this changes nothing until a deployment opts in.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.database import get_db_session
from yuantus.meta_engine.app_framework.entitlement_service import EntitlementService
from yuantus.meta_engine.services.date_effectivity_obsolete_service import (
    DateEffectivityObsoleteService,
)

logger = logging.getLogger(__name__)

ENTITLEMENT_FEATURE_KEY = "cadpdm_date_obsolete"


class DateObsoleteWorker:
    def __init__(
        self,
        *,
        worker_id: str = "cadpdm-date-obsolete-worker",
        batch_size: Optional[int] = None,
        poll_interval_seconds: Optional[int] = None,
        system_user_id: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.worker_id = worker_id
        self.batch_size = (
            batch_size
            if batch_size is not None
            else getattr(settings, "DATE_EFFECTIVITY_OBSOLETE_BATCH_SIZE", 100)
        )
        self.poll_interval_seconds = (
            poll_interval_seconds
            if poll_interval_seconds is not None
            else getattr(settings, "DATE_EFFECTIVITY_OBSOLETE_POLL_INTERVAL_SECONDS", 300)
        )
        self.system_user_id = (
            system_user_id
            if system_user_id is not None
            else getattr(settings, "DATE_EFFECTIVITY_OBSOLETE_SYSTEM_USER_ID", 0)
        )
        self._stop = False

    # -- gates ---------------------------------------------------------------
    @staticmethod
    def _globally_enabled() -> bool:
        return bool(getattr(get_settings(), "DATE_EFFECTIVITY_OBSOLETE_ENABLED", False))

    def _tenant_entitled(self, session: Session) -> bool:
        try:
            return bool(EntitlementService(session).is_entitled(ENTITLEMENT_FEATURE_KEY))
        except ValueError:
            # The feature key is mis-registered in FEATURE_APP_NAMES — surface it
            # LOUDLY rather than masking it as a silent "not entitled" (that broad
            # swallow is exactly how an unregistered key could hide). Still non-fatal
            # so the worker keeps polling.
            logger.error(
                "cadpdm-date-obsolete: entitlement key '%s' is not registered in "
                "FEATURE_APP_NAMES",
                ENTITLEMENT_FEATURE_KEY,
            )
            return False
        except Exception:  # operational (DB / tenant-scope) error -> non-fatal
            return False

    # -- run -----------------------------------------------------------------
    def run_once(self) -> int:
        """Process one batch in a managed (tenant-scoped) session. Returns the count
        processed. A no-op (0) when the global kill-switch is off."""
        if not self._globally_enabled():
            return 0
        with get_db_session() as session:
            return self.run_once_with_session(session)

    def run_once_with_session(self, session: Session) -> int:
        if not self._globally_enabled() or not self._tenant_entitled(session):
            return 0
        service = DateEffectivityObsoleteService(session)
        # process_expired is idempotent, so the whole expired set is drained each
        # tick (re-processing an already-Obsolete item is a cheap no-op). A per-tick
        # head slice would NOT converge — nothing retires a processed effectivity
        # from the scan, so the same head would be re-taken every tick and rows past
        # batch_size would never be reached. batch_size is therefore a backlog
        # WARNING threshold, not a correctness cap.
        expired = service.scan_expired()
        if len(expired) > self.batch_size:
            logger.warning(
                "cadpdm-date-obsolete-worker '%s': %d expired effectivities exceed "
                "batch_size %d (draining all this tick; idempotent)",
                self.worker_id, len(expired), self.batch_size,
            )
        processed = 0
        for eff in expired:
            try:
                service.process_expired(eff, user_id=self.system_user_id)
                session.commit()
                processed += 1
            except Exception as exc:  # one bad row never stops the sweep
                session.rollback()
                logger.warning(
                    "cadpdm-date-obsolete-worker '%s' failed on effectivity %s: %s",
                    self.worker_id, getattr(eff, "id", "?"), exc,
                )
        return processed

    def stop(self) -> None:
        self._stop = True

    def run_forever(self) -> None:  # pragma: no cover (operational loop)
        logger.info(
            "cadpdm-date-obsolete-worker '%s' starting (interval=%ss, enabled=%s)",
            self.worker_id, self.poll_interval_seconds, self._globally_enabled(),
        )
        while not self._stop:
            try:
                self.run_once()
            except Exception as exc:
                logger.exception("cadpdm-date-obsolete-worker tick error: %s", exc)
            time.sleep(self.poll_interval_seconds)
