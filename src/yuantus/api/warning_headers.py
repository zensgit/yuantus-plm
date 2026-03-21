from __future__ import annotations

from starlette.responses import Response

QUOTA_WARNING_HEADER = "X-Quota-Warning"
DOC_SYNC_CHECKOUT_WARNING_HEADER = "X-Doc-Sync-Checkout-Warning"


def append_warning_header(response: Response, header_name: str, warning: str | None) -> None:
    message = (warning or "").strip()
    if not message:
        return

    existing = response.headers.get(header_name)
    if existing:
        response.headers[header_name] = f"{existing}; {message}"
    else:
        response.headers[header_name] = message


def append_quota_warning(response: Response, warning: str | None) -> None:
    append_warning_header(response, QUOTA_WARNING_HEADER, warning)


def append_doc_sync_checkout_warning(response: Response, warning: str | None) -> None:
    append_warning_header(response, DOC_SYNC_CHECKOUT_WARNING_HEADER, warning)
