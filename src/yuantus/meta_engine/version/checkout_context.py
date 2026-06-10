"""Shared checkout workstation context helpers."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional


def normalize_checkout_context(
    *,
    client_host: Optional[str] = None,
    workspace_path: Optional[str] = None,
    client_info: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Normalize optional workstation context for item/file checkout locks."""
    normalized_info = dict(client_info or {}) if isinstance(client_info, Mapping) else None
    return {
        "client_host": str(client_host).strip() if client_host else None,
        "workspace_path": str(workspace_path).strip() if workspace_path else None,
        "client_info": normalized_info or None,
    }


def row_checkout_context(row: Any) -> dict[str, Any]:
    return {
        "client_host": getattr(row, "checkout_client_host", None),
        "workspace_path": getattr(row, "checkout_workspace_path", None),
        "client_info": getattr(row, "checkout_client_info", None),
    }


def apply_checkout_context(row: Any, context: dict[str, Any]) -> None:
    row.checkout_client_host = context.get("client_host")
    row.checkout_workspace_path = context.get("workspace_path")
    row.checkout_client_info = context.get("client_info")


def clear_checkout_context(row: Any) -> None:
    row.checkout_client_host = None
    row.checkout_workspace_path = None
    row.checkout_client_info = None


def has_identity_context(context: dict[str, Any]) -> bool:
    return bool(context.get("client_host") or context.get("workspace_path"))


def checkout_context_conflicts(row: Any, incoming: dict[str, Any]) -> bool:
    """Return True when same-user idempotency would cross workstation context.

    Legacy locks with no stored context remain idempotent, and callers that do not
    provide context remain backward-compatible. Once both sides provide a host/path
    identity, the pair must match exactly.
    """
    stored = row_checkout_context(row)
    if not has_identity_context(stored) or not has_identity_context(incoming):
        return False
    return (
        (stored.get("client_host") or ""),
        (stored.get("workspace_path") or ""),
    ) != (
        (incoming.get("client_host") or ""),
        (incoming.get("workspace_path") or ""),
    )
