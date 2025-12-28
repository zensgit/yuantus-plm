from __future__ import annotations

from typing import Any, Dict, Optional


class PLMException(Exception):
    """
    Lightweight but compatible base exception.

    The migrated Meta Engine code expects:
    - attributes: message/code/status_code/details/user_message
    - method: to_dict()
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "PLM_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details: Dict[str, Any] = details or {}
        self.user_message = user_message or message
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
        }

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class ValidationError(PLMException):
    def __init__(self, message: str, field: Optional[str] = None, **kwargs: Any):
        details: Dict[str, Any] = {"field": field} if field else {}
        details.update(kwargs)
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
            user_message=f"Validation failed: {message}",
        )


class PermissionError(PLMException):
    _KNOWN_ACTIONS = {"add", "get", "update", "delete", "promote"}

    def __init__(self, action: str, resource: Optional[str] = None, **kwargs: Any):
        # Compatibility: some legacy code raises PermissionError("free form message")
        if resource is None and (" " in action) and action not in self._KNOWN_ACTIONS:
            super().__init__(
                message=action,
                code="PERMISSION_DENIED",
                status_code=403,
                details=dict(kwargs),
                user_message=action,
            )
            return

        message = f"Permission denied for action: {action}"
        if resource:
            message += f" on resource: {resource}"

        details: Dict[str, Any] = {"action": action, "resource": resource}
        details.update(kwargs)
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=403,
            details=details,
            user_message="You don't have permission to perform this action",
        )


class StateLockedError(PLMException):
    def __init__(self, state: str, resource: Optional[str] = None, **kwargs: Any):
        message = f"Item is locked in state: {state}"
        details: Dict[str, Any] = {"state": state, "resource": resource}
        details.update(kwargs)
        super().__init__(
            message=message,
            code="STATE_LOCKED",
            status_code=409,
            details=details,
            user_message=message,
        )


class ConfigurationError(PLMException):
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs: Any):
        details: Dict[str, Any] = {"config_key": config_key} if config_key else {}
        details.update(kwargs)
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            details=details,
            user_message="System configuration error",
        )


class QuotaExceededError(PLMException):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Quota exceeded",
            code="QUOTA_EXCEEDED",
            status_code=429,
            details=details or {},
            user_message="Quota exceeded",
        )
