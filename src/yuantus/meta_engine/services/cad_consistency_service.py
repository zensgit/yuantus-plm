"""WP1.3 CAD 2D/3D staleness service.

Determines whether a part's 2D drawing(s) are stale relative to its 3D model,
using PROVENANCE (not raw batch-id inequality, which is unsound because batch ids
are opaque/unordered). A drawing pins the model batch it was last co-saved with
(``source_batch_id``); it is stale only when the model has moved past that pin.

Design is locked in
``docs/DEVELOPMENT_WP1_3_CAD_2D3D_STALENESS_GROUNDING_TASKBOOK_20260605.md``:

- Selector (``document_type`` authoritative, ``file_role`` constrains):
  - Model M  = document_type "3d" AND file_role "native_cad".
  - Drawing D = document_type "2d" AND file_role in {drawing, native_cad}
    (excludes preview/geometry/printout/attachment so PDF printouts / image
    previews are not treated as drawings).
- Provenance pin: in recompute, when a drawing and the model share the same
  import_batch_id (a "save all"), pin D.source_batch_id = M.import_batch_id.
  A drawing-only re-import does NOT repin.
- Verdict: no model -> no_model; null provenance -> unknown (fail-open);
  pinned == model batch -> up_to_date; pinned != model batch -> model_moved_on
  (stale). Timestamps are advisory only (never drive needs_update).
- ItemFile is the current-state authority; recompute mirrors only the CURRENT
  version's VersionFile rows (never historical snapshots).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from yuantus.meta_engine.events.domain_events import CadDrawingStalenessChangedEvent
from yuantus.meta_engine.events.transactional import enqueue_event
from yuantus.meta_engine.models.file import (
    DocumentType,
    FileContainer,
    FileRole,
    ItemFile,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.models import VersionFile

_NATIVE_CAD = FileRole.NATIVE_CAD.value
_DRAWING = FileRole.DRAWING.value
_DOC_3D = DocumentType.CAD_3D.value  # "3d"
_DOC_2D = DocumentType.CAD_2D.value  # "2d"

# A 2D drawing candidate may carry file_role "drawing" (normal) or "native_cad"
# (a 2D DWG mislabeled by the client -- document_type="2d" is authoritative). It
# must NOT be preview/geometry/printout/attachment.
_DRAWING_ROLES = frozenset({_DRAWING, _NATIVE_CAD})

# Staleness reasons (drive needs_update only for model_moved_on).
REASON_NO_MODEL = "no_model"
REASON_UNKNOWN = "unknown"
REASON_UP_TO_DATE = "up_to_date"
REASON_MODEL_MOVED_ON = "model_moved_on"
REASON_AMBIGUOUS = "ambiguous"

_MODEL_AMBIGUOUS = "ambiguous"
_MODEL_OK = "ok"
_MODEL_NONE = "none"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _time_hint(fc: FileContainer) -> Optional[datetime]:
    return getattr(fc, "updated_at", None) or getattr(fc, "created_at", None)


class CadConsistencyService:
    def __init__(self, session: Session):
        self.session = session

    # ----- selection -------------------------------------------------------
    def _current_item_files(
        self, item_id: str
    ) -> List[Tuple[ItemFile, FileContainer]]:
        return (
            self.session.query(ItemFile, FileContainer)
            .join(FileContainer, FileContainer.id == ItemFile.file_id)
            .filter(ItemFile.item_id == item_id)
            .all()
        )

    def _select_model(
        self, rows: List[Tuple[ItemFile, FileContainer]]
    ) -> Tuple[str, Optional[Tuple[ItemFile, FileContainer]]]:
        models = [
            (itf, fc)
            for (itf, fc) in rows
            if fc.document_type == _DOC_3D and itf.file_role == _NATIVE_CAD
        ]
        if len(models) > 1:
            return _MODEL_AMBIGUOUS, None
        if not models:
            return _MODEL_NONE, None
        return _MODEL_OK, models[0]

    def _select_drawings(
        self, rows: List[Tuple[ItemFile, FileContainer]]
    ) -> List[Tuple[ItemFile, FileContainer]]:
        return [
            (itf, fc)
            for (itf, fc) in rows
            if fc.document_type == _DOC_2D and itf.file_role in _DRAWING_ROLES
        ]

    # ----- verdict ---------------------------------------------------------
    def _verdict(
        self, drawing: ItemFile, model_status: str, model_batch: Optional[str]
    ) -> Tuple[str, bool]:
        """Returns (reason, needs_update). Mutates drawing.source_batch_id (pin)."""
        if model_status == _MODEL_AMBIGUOUS:
            return REASON_AMBIGUOUS, False
        if model_status != _MODEL_OK:
            return REASON_NO_MODEL, False

        # Provenance pin: only when drawing and model were co-saved (same batch).
        if (
            drawing.import_batch_id is not None
            and model_batch is not None
            and drawing.import_batch_id == model_batch
        ):
            drawing.source_batch_id = model_batch

        if drawing.source_batch_id is None or model_batch is None:
            # Never co-saved with a (batched) model -> unknown / fail-open.
            return REASON_UNKNOWN, False
        if drawing.source_batch_id == model_batch:
            return REASON_UP_TO_DATE, False
        return REASON_MODEL_MOVED_ON, True

    def _mirror_to_current_version(
        self, version_id: str, drawing: ItemFile
    ) -> None:
        vf = (
            self.session.query(VersionFile)
            .filter_by(
                version_id=version_id,
                file_id=drawing.file_id,
                file_role=drawing.file_role,
            )
            .first()
        )
        if vf is not None:
            vf.needs_update = bool(drawing.needs_update)
            vf.staleness_reason = drawing.staleness_reason
            vf.staleness_checked_at = drawing.staleness_checked_at
            vf.source_batch_id = drawing.source_batch_id
            self.session.add(vf)

    # ----- public API ------------------------------------------------------
    def recompute(self, item_id: str) -> Dict[str, Any]:
        """Pin provenance and materialize needs_update for the item's drawings.
        Writes ItemFile (current authority) + the CURRENT version's VersionFile
        mirror only. Enqueues a flip event per drawing whose verdict changed.
        Commits."""
        rows = self._current_item_files(item_id)
        model_status, model = self._select_model(rows)
        model_batch = model[0].import_batch_id if model else None
        drawings = self._select_drawings(rows)

        item = self.session.get(Item, item_id)
        current_version_id = item.current_version_id if item else None

        results: List[Dict[str, Any]] = []
        flips: List[Tuple[str, bool, bool, Optional[str]]] = []
        now = _utcnow()

        for (d_itf, _d_fc) in drawings:
            previous = bool(d_itf.needs_update)
            reason, needs = self._verdict(d_itf, model_status, model_batch)
            d_itf.needs_update = needs
            d_itf.staleness_reason = reason
            d_itf.staleness_checked_at = now
            self.session.add(d_itf)
            if current_version_id:
                self._mirror_to_current_version(current_version_id, d_itf)
            if needs != previous:
                flips.append((d_itf.file_id, previous, needs, reason))
            results.append(
                {
                    "file_id": d_itf.file_id,
                    "file_role": d_itf.file_role,
                    "needs_update": needs,
                    "staleness_reason": reason,
                    "source_batch_id": d_itf.source_batch_id,
                }
            )

        self.session.flush()
        for (file_id, previous, needs, reason) in flips:
            enqueue_event(
                self.session,
                CadDrawingStalenessChangedEvent(
                    item_id=item_id,
                    drawing_file_id=file_id,
                    needs_update=needs,
                    previous_needs_update=previous,
                    staleness_reason=reason,
                ),
            )
        self.session.commit()

        return {
            "item_id": item_id,
            "model_status": model_status,
            "model_import_batch_id": model_batch,
            "drawing_count": len(results),
            "stale_count": sum(1 for r in results if r["needs_update"]),
            "drawings": results,
        }

    def get_staleness(self, item_id: str) -> Dict[str, Any]:
        """Read-only staleness view for the item (does not recompute). The
        ``time_hint`` is advisory only and never drives needs_update."""
        rows = self._current_item_files(item_id)
        model_status, model = self._select_model(rows)
        drawings = self._select_drawings(rows)

        model_info: Optional[Dict[str, Any]] = None
        model_batch: Optional[str] = None
        if model:
            m_itf, m_fc = model
            model_batch = m_itf.import_batch_id
            model_info = {
                "file_id": m_itf.file_id,
                "import_batch_id": m_itf.import_batch_id,
                "time_hint": _time_hint(m_fc),
            }

        out_drawings: List[Dict[str, Any]] = []
        for (d_itf, d_fc) in drawings:
            out_drawings.append(
                {
                    "file_id": d_itf.file_id,
                    "file_role": d_itf.file_role,
                    "needs_update": bool(d_itf.needs_update),
                    "staleness_reason": d_itf.staleness_reason,
                    "source_batch_id": d_itf.source_batch_id,
                    "import_batch_id": d_itf.import_batch_id,
                    "time_hint": _time_hint(d_fc),
                }
            )

        return {
            "item_id": item_id,
            "model_status": model_status,
            "model": model_info,
            "model_import_batch_id": model_batch,
            "drawing_count": len(out_drawings),
            "stale_count": sum(1 for d in out_drawings if d["needs_update"]),
            "drawings": out_drawings,
        }
