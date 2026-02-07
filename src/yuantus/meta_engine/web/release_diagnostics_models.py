from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from yuantus.meta_engine.services.release_validation import ValidationIssue


class ReleaseDiagnosticIssue(BaseModel):
    code: str
    message: str
    rule_id: str
    details: Optional[Dict[str, Any]] = None


class ReleaseDiagnosticsResponse(BaseModel):
    ok: bool
    resource_type: str
    resource_id: str
    ruleset_id: str
    errors: List[ReleaseDiagnosticIssue] = Field(default_factory=list)
    warnings: List[ReleaseDiagnosticIssue] = Field(default_factory=list)


def issue_to_response(issue: Any) -> ReleaseDiagnosticIssue:
    if isinstance(issue, ReleaseDiagnosticIssue):
        return issue
    if isinstance(issue, ValidationIssue):
        return ReleaseDiagnosticIssue(
            code=str(issue.code or ""),
            message=str(issue.message or ""),
            rule_id=str(issue.rule_id or ""),
            details=issue.details,
        )
    if isinstance(issue, dict):
        return ReleaseDiagnosticIssue(
            code=str(issue.get("code") or ""),
            message=str(issue.get("message") or ""),
            rule_id=str(issue.get("rule_id") or ""),
            details=issue.get("details"),
        )
    return ReleaseDiagnosticIssue(
        code=str(getattr(issue, "code", "") or ""),
        message=str(getattr(issue, "message", "") or ""),
        rule_id=str(getattr(issue, "rule_id", "") or ""),
        details=getattr(issue, "details", None),
    )

