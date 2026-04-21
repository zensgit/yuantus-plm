"""Locale and report locale API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.meta_engine.locale.service import LocaleService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.report_locale.service import ReportLocaleService

locale_router = APIRouter(prefix="/locale", tags=["Locale"])


# ============================================================================
# Request Models
# ============================================================================


class TranslationUpsertRequest(BaseModel):
    record_type: str
    record_id: str
    field_name: str
    lang: str
    translated_value: str
    source_value: Optional[str] = None
    state: str = "draft"
    module: Optional[str] = None


class TranslationBulkRequest(BaseModel):
    translations: List[TranslationUpsertRequest]


class TranslationResolveRequest(BaseModel):
    record_type: str
    record_id: str
    fields: List[str]
    lang: str
    fallback_langs: List[str] = Field(default_factory=list)


class ReportProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    lang: str = "en_US"
    fallback_lang: Optional[str] = None
    number_format: str = "#,##0.00"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm:ss"
    timezone: str = "UTC"
    paper_size: str = "a4"
    orientation: str = "portrait"
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    logo_path: Optional[str] = None
    report_type: Optional[str] = None
    is_default: bool = False
    properties: Optional[Dict[str, Any]] = None


class ReportProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    lang: Optional[str] = None
    number_format: Optional[str] = None
    date_format: Optional[str] = None
    paper_size: Optional[str] = None
    orientation: Optional[str] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    is_default: Optional[bool] = None


# ============================================================================
# Helpers
# ============================================================================


def _translation_dict(t) -> dict:
    return {
        "id": t.id,
        "record_type": t.record_type,
        "record_id": t.record_id,
        "field_name": t.field_name,
        "lang": t.lang,
        "source_value": t.source_value,
        "translated_value": t.translated_value,
        "state": t.state,
        "module": t.module,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _profile_dict(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "lang": p.lang,
        "fallback_lang": p.fallback_lang,
        "number_format": p.number_format,
        "date_format": p.date_format,
        "time_format": p.time_format,
        "timezone": p.timezone,
        "paper_size": p.paper_size,
        "orientation": p.orientation,
        "header_text": p.header_text,
        "footer_text": p.footer_text,
        "logo_path": p.logo_path,
        "report_type": p.report_type,
        "is_default": p.is_default,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _normalize_query_list(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    result: List[str] = []
    for raw in values:
        for part in str(raw).split(","):
            value = part.strip()
            if value and value not in result:
                result.append(value)
    return result or None


# ============================================================================
# Translation Endpoints
# ============================================================================


@locale_router.post("/translations")
async def upsert_translation(
    req: TranslationUpsertRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = LocaleService(db)
    try:
        t = svc.upsert_translation(
            record_type=req.record_type,
            record_id=req.record_id,
            field_name=req.field_name,
            lang=req.lang,
            translated_value=req.translated_value,
            source_value=req.source_value,
            state=req.state,
            module=req.module,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _translation_dict(t)


@locale_router.post("/translations/bulk")
async def bulk_upsert_translations(
    req: TranslationBulkRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = LocaleService(db)
    result = svc.bulk_upsert(
        [t.model_dump(mode="json") for t in req.translations],
        user_id=user_id,
    )
    db.commit()
    return result


@locale_router.get("/translations")
async def get_translations(
    record_type: str = Query(...),
    record_id: str = Query(...),
    lang: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = LocaleService(db)
    items = svc.get_translations_for_record(
        record_type=record_type, record_id=record_id, lang=lang
    )
    return {"total": len(items), "translations": [_translation_dict(t) for t in items]}


@locale_router.get("/translations/by-lang")
async def get_translations_by_lang(
    lang: str = Query(...),
    record_type: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = LocaleService(db)
    items = svc.get_translations_by_lang(
        lang=lang, record_type=record_type, module=module, state=state
    )
    return {"total": len(items), "translations": [_translation_dict(t) for t in items]}


# ============================================================================
# Report Locale Profile Endpoints
# ============================================================================


@locale_router.post("/report-profiles")
async def create_report_profile(
    req: ReportProfileCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = ReportLocaleService(db)
    try:
        p = svc.create_profile(
            name=req.name,
            lang=req.lang,
            fallback_lang=req.fallback_lang,
            number_format=req.number_format,
            date_format=req.date_format,
            time_format=req.time_format,
            timezone=req.timezone,
            paper_size=req.paper_size,
            orientation=req.orientation,
            header_text=req.header_text,
            footer_text=req.footer_text,
            logo_path=req.logo_path,
            report_type=req.report_type,
            is_default=req.is_default,
            properties=req.properties,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _profile_dict(p)


@locale_router.get("/report-profiles")
async def list_report_profiles(
    lang: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
    is_default: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    svc = ReportLocaleService(db)
    profiles = svc.list_profiles(
        lang=lang, report_type=report_type, is_default=is_default
    )
    return {"total": len(profiles), "profiles": [_profile_dict(p) for p in profiles]}


@locale_router.get("/report-profiles/resolve")
async def resolve_report_profile(
    lang: str = Query(...),
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = ReportLocaleService(db)
    profile = svc.resolve_profile(lang=lang, report_type=report_type)
    if not profile:
        raise HTTPException(status_code=404, detail="No matching profile found")
    return _profile_dict(profile)


@locale_router.get("/report-profiles/{profile_id}")
async def get_report_profile(profile_id: str, db: Session = Depends(get_db)):
    svc = ReportLocaleService(db)
    p = svc.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_dict(p)


@locale_router.patch("/report-profiles/{profile_id}")
async def update_report_profile(
    profile_id: str,
    req: ReportProfileUpdateRequest,
    db: Session = Depends(get_db),
):
    svc = ReportLocaleService(db)
    fields = {k: v for k, v in req.model_dump(exclude_unset=True).items()}
    p = svc.update_profile(profile_id, **fields)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.commit()
    return _profile_dict(p)


@locale_router.delete("/report-profiles/{profile_id}")
async def delete_report_profile(profile_id: str, db: Session = Depends(get_db)):
    svc = ReportLocaleService(db)
    deleted = svc.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.commit()
    return {"deleted": True}


@locale_router.post("/translations/resolve")
async def resolve_translations(
    req: TranslationResolveRequest,
    db: Session = Depends(get_db),
):
    svc = LocaleService(db)
    return svc.resolve_translations_batch(
        record_type=req.record_type,
        record_id=req.record_id,
        fields=req.fields,
        lang=req.lang,
        fallback_langs=req.fallback_langs or None,
    )


@locale_router.get("/translations/fallback-preview")
async def fallback_preview(
    record_type: str = Query(...),
    record_id: str = Query(...),
    field_name: str = Query(...),
    lang: str = Query(...),
    fallback_langs: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
):
    svc = LocaleService(db)
    normalized_fallbacks = _normalize_query_list(fallback_langs)

    return svc.fallback_preview(
        record_type=record_type,
        record_id=record_id,
        field_name=field_name,
        lang=lang,
        fallback_langs=normalized_fallbacks,
    )


@locale_router.get("/items/{item_id}/localized-fields")
async def resolve_item_localized_fields(
    item_id: str,
    lang: str = Query(...),
    fields: Optional[List[str]] = Query(None),
    fallback_langs: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    normalized_fields = _normalize_query_list(fields) or ["name", "description"]
    normalized_fallbacks = _normalize_query_list(fallback_langs)
    svc = LocaleService(db)
    return svc.resolve_item_localized_fields(
        item,
        fields=normalized_fields,
        lang=lang,
        fallback_langs=normalized_fallbacks,
    )


@locale_router.get("/export-context")
async def get_export_context(
    lang: str = Query(...),
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = ReportLocaleService(db)
    return svc.get_export_context(lang=lang, report_type=report_type)
