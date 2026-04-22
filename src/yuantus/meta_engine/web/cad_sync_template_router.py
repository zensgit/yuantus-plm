from __future__ import annotations

import csv
import io
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, require_admin_user
from yuantus.database import get_db
from yuantus.integrations.cad_connectors import resolve_cad_sync_key
from yuantus.meta_engine.models.meta_schema import ItemType

cad_sync_template_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadSyncTemplateRow(BaseModel):
    property_name: str
    label: Optional[str] = None
    data_type: Optional[str] = None
    is_cad_synced: bool = False
    cad_key: Optional[str] = None


class CadSyncTemplateResponse(BaseModel):
    item_type_id: str
    properties: List[CadSyncTemplateRow]


class CadSyncTemplateApplyResponse(BaseModel):
    item_type_id: str
    updated: int
    skipped: int
    missing: List[str] = Field(default_factory=list)


def _csv_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


@cad_sync_template_router.get(
    "/sync-template/{item_type_id}", response_model=CadSyncTemplateResponse
)
def get_cad_sync_template(
    item_type_id: str,
    output_format: str = "csv",
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    rows: List[CadSyncTemplateRow] = []
    for prop in item_type.properties or []:
        cad_key = None
        if prop.is_cad_synced:
            cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
        rows.append(
            CadSyncTemplateRow(
                property_name=prop.name,
                label=prop.label,
                data_type=prop.data_type,
                is_cad_synced=bool(prop.is_cad_synced),
                cad_key=cad_key,
            )
        )

    if output_format.lower() == "json":
        return CadSyncTemplateResponse(item_type_id=item_type_id, properties=rows)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["property_name", "label", "data_type", "is_cad_synced", "cad_key"])
    for row in rows:
        writer.writerow(
            [
                row.property_name,
                row.label or "",
                row.data_type or "",
                "true" if row.is_cad_synced else "false",
                row.cad_key or "",
            ]
        )
    output.seek(0)
    filename = f"cad_sync_template_{item_type_id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)


@cad_sync_template_router.post(
    "/sync-template/{item_type_id}", response_model=CadSyncTemplateApplyResponse
)
async def apply_cad_sync_template(
    item_type_id: str,
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> CadSyncTemplateApplyResponse:
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty template file")

    text = payload.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    props_by_name = {prop.name: prop for prop in (item_type.properties or [])}

    updated = 0
    skipped = 0
    missing: List[str] = []

    for row in reader:
        name = (row.get("property_name") or row.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        prop = props_by_name.get(name)
        if not prop:
            missing.append(name)
            continue

        cad_key = (row.get("cad_key") or row.get("cad_attribute") or "").strip()
        sync_flag = _csv_bool(row.get("is_cad_synced"))
        changed = False

        if sync_flag is not None and prop.is_cad_synced != sync_flag:
            prop.is_cad_synced = sync_flag
            changed = True

        if cad_key or sync_flag:
            ui_opts = prop.ui_options
            if isinstance(ui_opts, str):
                try:
                    ui_opts = json.loads(ui_opts)
                except Exception:
                    ui_opts = {}
            if not isinstance(ui_opts, dict):
                ui_opts = {}
            if cad_key:
                ui_opts["cad_key"] = cad_key
            else:
                ui_opts.pop("cad_key", None)
            prop.ui_options = ui_opts
            changed = True

        if changed:
            db.add(prop)
            updated += 1
        else:
            skipped += 1

    if updated:
        item_type.properties_schema = None
        db.add(item_type)
    db.commit()

    return CadSyncTemplateApplyResponse(
        item_type_id=item_type_id,
        updated=updated,
        skipped=skipped,
        missing=missing,
    )
