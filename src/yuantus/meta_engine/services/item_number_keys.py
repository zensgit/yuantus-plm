from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional


ITEM_NUMBER_READ_KEYS = ("item_number", "number")


def get_item_number(payload: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not payload:
        return None

    for key in ITEM_NUMBER_READ_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def ensure_item_number_aliases(properties: Optional[dict], value: Optional[str]) -> dict:
    props = dict(properties or {})
    if value is None:
        return props
    text = str(value).strip()
    if not text:
        return props
    props["item_number"] = text
    props["number"] = text
    return props
