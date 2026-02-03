"""Electronic signature service layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import csv
import hashlib
import hmac
import io
import json
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from yuantus.meta_engine.esign.models import (
    ElectronicSignature,
    SignatureAuditLog,
    SignatureManifest,
    SigningReason,
    SignatureStatus,
)
from yuantus.meta_engine.models.item import Item
from yuantus.security.auth.service import AuthService
from yuantus.security.rbac.models import RBACUser


class ElectronicSignatureService:
    def __init__(
        self,
        session: Session,
        *,
        secret_key: str,
        auth_service: Optional[AuthService] = None,
    ) -> None:
        self.session = session
        self.secret_key = secret_key
        self.auth_service = auth_service

    def sign(
        self,
        *,
        item_id: str,
        user_id: int,
        tenant_id: Optional[str],
        meaning: str,
        password: Optional[str] = None,
        reason_id: Optional[str] = None,
        reason_text: Optional[str] = None,
        comment: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_info: Optional[Dict[str, Any]] = None,
        workflow_instance_id: Optional[str] = None,
        workflow_activity_id: Optional[str] = None,
    ) -> ElectronicSignature:
        item = self.session.get(Item, item_id)
        if not item:
            raise ValueError(f"Item not found: {item_id}")

        user = self.session.get(RBACUser, user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        reason: Optional[SigningReason] = None
        if reason_id:
            reason = self.session.get(SigningReason, reason_id)
            if not reason:
                raise ValueError("Signing reason not found")
            reason_text = reason_text or reason.name

        if reason and reason.requires_password:
            if not password:
                raise ValueError("Password required for this signature type")
            if not self._verify_password(tenant_id, user.username, password):
                self._log_audit(
                    "sign",
                    item_id=item_id,
                    actor_id=user_id,
                    actor_username=user.username,
                    success=False,
                    error_message="Invalid password",
                    client_ip=client_ip,
                )
                raise ValueError("Invalid password")

        if reason and reason.requires_comment and not comment:
            raise ValueError("Comment required for this signature type")

        signed_at = datetime.utcnow()
        content_hash = self._calculate_content_hash(item)
        signature_hash = self._calculate_signature_hash(
            item_id=item.id,
            item_generation=item.generation,
            user_id=user_id,
            meaning=meaning,
            content_hash=content_hash,
            timestamp=signed_at,
        )

        signature = ElectronicSignature(
            id=str(uuid.uuid4()),
            item_id=item.id,
            item_generation=item.generation,
            signer_id=user_id,
            signer_username=user.username,
            signer_full_name=user.username,
            reason_id=reason_id,
            meaning=meaning,
            reason_text=reason_text,
            comment=comment,
            signature_hash=signature_hash,
            content_hash=content_hash,
            client_ip=client_ip,
            client_info=client_info,
            workflow_instance_id=workflow_instance_id,
            workflow_activity_id=workflow_activity_id,
            signed_at=signed_at,
        )
        self.session.add(signature)
        self.session.flush()

        self._update_manifest(item.id, item.generation)

        self._log_audit(
            "sign",
            signature_id=signature.id,
            item_id=item_id,
            actor_id=user_id,
            actor_username=user.username,
            details={
                "meaning": meaning,
                "reason": reason_text,
            },
            client_ip=client_ip,
        )

        self.session.commit()
        return signature

    def verify(self, signature_id: str) -> Dict[str, Any]:
        signature = self.session.get(ElectronicSignature, signature_id)
        if not signature:
            raise ValueError("Signature not found")

        item = self.session.get(Item, signature.item_id)

        issues: List[str] = []
        is_valid = True

        if signature.status != SignatureStatus.VALID.value:
            is_valid = False
            issues.append(f"Signature status is {signature.status}")

        if item and item.generation == signature.item_generation:
            current_hash = self._calculate_content_hash(item)
            if current_hash != signature.content_hash:
                is_valid = False
                issues.append("Content has been modified since signing")

        expected_hash = self._calculate_signature_hash(
            item_id=signature.item_id,
            item_generation=signature.item_generation,
            user_id=signature.signer_id,
            meaning=signature.meaning,
            content_hash=signature.content_hash,
            timestamp=signature.signed_at,
        )
        if expected_hash != signature.signature_hash:
            is_valid = False
            issues.append("Signature hash mismatch")

        self._log_audit(
            "verify",
            signature_id=signature_id,
            item_id=signature.item_id,
            actor_id=signature.signer_id,
            actor_username=signature.signer_username,
            details={"is_valid": is_valid, "issues": issues},
        )
        self.session.commit()

        return {
            "signature_id": signature_id,
            "is_valid": is_valid,
            "issues": issues,
            "signature": {
                "id": signature.id,
                "signer": signature.signer_full_name,
                "meaning": signature.meaning,
                "signed_at": signature.signed_at.isoformat() if signature.signed_at else None,
                "status": signature.status,
            },
        }

    def revoke(
        self,
        *,
        signature_id: str,
        revoked_by_id: int,
        reason: str,
    ) -> ElectronicSignature:
        signature = self.session.get(ElectronicSignature, signature_id)
        if not signature:
            raise ValueError("Signature not found")

        if signature.status == SignatureStatus.REVOKED.value:
            raise ValueError("Signature is already revoked")

        signature.status = SignatureStatus.REVOKED.value
        signature.revoked_at = datetime.utcnow()
        signature.revoked_by_id = revoked_by_id
        signature.revocation_reason = reason
        self.session.add(signature)

        revoker = self.session.get(RBACUser, revoked_by_id)

        self._log_audit(
            "revoke",
            signature_id=signature_id,
            item_id=signature.item_id,
            actor_id=revoked_by_id,
            actor_username=revoker.username if revoker else "unknown",
            details={"reason": reason},
        )
        self.session.commit()
        return signature

    def get_signatures(
        self,
        *,
        item_id: str,
        generation: Optional[int] = None,
        include_revoked: bool = False,
    ) -> List[Dict[str, Any]]:
        query = self.session.query(ElectronicSignature).filter(
            ElectronicSignature.item_id == item_id
        )

        if generation is not None:
            query = query.filter(ElectronicSignature.item_generation == generation)

        if not include_revoked:
            query = query.filter(ElectronicSignature.status == SignatureStatus.VALID.value)

        signatures = query.order_by(ElectronicSignature.signed_at).all()

        return [
            {
                "id": s.id,
                "signer_id": s.signer_id,
                "signer_name": s.signer_full_name,
                "meaning": s.meaning,
                "reason": s.reason_text,
                "comment": s.comment,
                "signed_at": s.signed_at.isoformat() if s.signed_at else None,
                "status": s.status,
                "item_generation": s.item_generation,
            }
            for s in signatures
        ]

    def create_signing_reason(
        self,
        *,
        code: str,
        name: str,
        meaning: str,
        description: Optional[str] = None,
        regulatory_reference: Optional[str] = None,
        requires_password: bool = True,
        requires_comment: bool = False,
        item_type_id: Optional[str] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        sequence: int = 0,
    ) -> SigningReason:
        reason = SigningReason(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            meaning=meaning,
            description=description,
            regulatory_reference=regulatory_reference,
            requires_password=requires_password,
            requires_comment=requires_comment,
            item_type_id=item_type_id,
            from_state=from_state,
            to_state=to_state,
            sequence=sequence,
            is_active=True,
        )
        self.session.add(reason)
        self.session.commit()
        return reason

    def list_signing_reasons(
        self,
        *,
        item_type_id: Optional[str] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        meaning: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[SigningReason]:
        query = self.session.query(SigningReason)
        if not include_inactive:
            query = query.filter(SigningReason.is_active.is_(True))

        conditions = [SigningReason.item_type_id.is_(None)]
        if item_type_id:
            conditions.append(SigningReason.item_type_id == item_type_id)
        query = query.filter(or_(*conditions))

        if from_state:
            query = query.filter(
                or_(SigningReason.from_state.is_(None), SigningReason.from_state == from_state)
            )
        if to_state:
            query = query.filter(
                or_(SigningReason.to_state.is_(None), SigningReason.to_state == to_state)
            )
        if meaning:
            query = query.filter(SigningReason.meaning == meaning)

        return query.order_by(SigningReason.sequence).all()

    def update_signing_reason(
        self,
        reason_id: str,
        *,
        code: Optional[str] = None,
        name: Optional[str] = None,
        meaning: Optional[str] = None,
        description: Optional[str] = None,
        regulatory_reference: Optional[str] = None,
        requires_password: Optional[bool] = None,
        requires_comment: Optional[bool] = None,
        item_type_id: Optional[str] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        sequence: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> SigningReason:
        reason = self.session.get(SigningReason, reason_id)
        if not reason:
            raise ValueError("Signing reason not found")

        if code is not None:
            reason.code = code
        if name is not None:
            reason.name = name
        if meaning is not None:
            reason.meaning = meaning
        if description is not None:
            reason.description = description
        if regulatory_reference is not None:
            reason.regulatory_reference = regulatory_reference
        if requires_password is not None:
            reason.requires_password = requires_password
        if requires_comment is not None:
            reason.requires_comment = requires_comment
        if item_type_id is not None:
            reason.item_type_id = item_type_id
        if from_state is not None:
            reason.from_state = from_state
        if to_state is not None:
            reason.to_state = to_state
        if sequence is not None:
            reason.sequence = sequence
        if is_active is not None:
            reason.is_active = is_active

        self.session.add(reason)
        self.session.commit()
        return reason

    def create_manifest(
        self,
        *,
        item_id: str,
        generation: int,
        required_signatures: List[Dict[str, Any]],
    ) -> SignatureManifest:
        manifest = SignatureManifest(
            id=str(uuid.uuid4()),
            item_id=item_id,
            item_generation=generation,
            required_signatures=required_signatures,
        )
        self.session.add(manifest)
        self.session.commit()
        return manifest

    def get_manifest_status(
        self,
        *,
        item_id: str,
        generation: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        item = self.session.get(Item, item_id)
        if not item:
            return None

        gen = generation or item.generation

        manifest = (
            self.session.query(SignatureManifest)
            .filter(
                SignatureManifest.item_id == item_id,
                SignatureManifest.item_generation == gen,
            )
            .first()
        )

        if not manifest:
            return None

        signatures = self.get_signatures(item_id=item_id, generation=gen)
        signed_meanings = {s["meaning"] for s in signatures}

        required = manifest.required_signatures or []
        status_list = []
        for req in required:
            meaning = req.get("meaning")
            status_list.append(
                {
                    "meaning": meaning,
                    "role": req.get("role"),
                    "required": req.get("required", False),
                    "signed": meaning in signed_meanings,
                    "signature": next(
                        (s for s in signatures if s["meaning"] == meaning),
                        None,
                    ),
                }
            )

        return {
            "manifest_id": manifest.id,
            "item_id": item_id,
            "generation": gen,
            "is_complete": manifest.is_complete,
            "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
            "requirements": status_list,
        }

    def _verify_password(self, tenant_id: Optional[str], username: str, password: str) -> bool:
        if not self.auth_service:
            return False
        if not tenant_id:
            return False
        try:
            self.auth_service.authenticate(
                tenant_id=tenant_id, username=username, password=password
            )
            return True
        except Exception:
            return False

    def _calculate_content_hash(self, item: Item) -> str:
        payload = {
            "id": item.id,
            "generation": item.generation,
            "config_id": item.config_id,
            "state": item.state,
            "properties": item.properties or {},
        }
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()

    def _calculate_signature_hash(
        self,
        *,
        item_id: str,
        item_generation: int,
        user_id: int,
        meaning: str,
        content_hash: str,
        timestamp: datetime,
    ) -> str:
        message = f"{item_id}:{item_generation}:{user_id}:{meaning}:{content_hash}:{timestamp.isoformat()}"
        return hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

    def _update_manifest(self, item_id: str, generation: int) -> None:
        manifest = (
            self.session.query(SignatureManifest)
            .filter(
                SignatureManifest.item_id == item_id,
                SignatureManifest.item_generation == generation,
            )
            .first()
        )

        if not manifest:
            return

        signatures = (
            self.session.query(ElectronicSignature)
            .filter(
                ElectronicSignature.item_id == item_id,
                ElectronicSignature.item_generation == generation,
                ElectronicSignature.status == SignatureStatus.VALID.value,
            )
            .all()
        )

        required = manifest.required_signatures or []
        signed_meanings = {s.meaning for s in signatures}

        is_complete = all(
            req.get("meaning") in signed_meanings
            for req in required
            if req.get("required", False)
        )

        if is_complete and not manifest.is_complete:
            manifest.is_complete = True
            manifest.completed_at = datetime.utcnow()
            self.session.add(manifest)

    def _log_audit(
        self,
        action: str,
        *,
        signature_id: Optional[str] = None,
        item_id: Optional[str] = None,
        actor_id: int,
        actor_username: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        ) -> None:
        log = SignatureAuditLog(
            id=str(uuid.uuid4()),
            action=action,
            signature_id=signature_id,
            item_id=item_id,
            actor_id=actor_id,
            actor_username=actor_username,
            details=details,
            success=success,
            error_message=error_message,
            client_ip=client_ip,
        )
        self.session.add(log)

    def list_audit_logs(
        self,
        *,
        item_id: Optional[str] = None,
        signature_id: Optional[str] = None,
        actor_id: Optional[int] = None,
        action: Optional[str] = None,
        success: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[SignatureAuditLog]:
        query = self.session.query(SignatureAuditLog)
        if item_id:
            query = query.filter(SignatureAuditLog.item_id == item_id)
        if signature_id:
            query = query.filter(SignatureAuditLog.signature_id == signature_id)
        if actor_id is not None:
            query = query.filter(SignatureAuditLog.actor_id == actor_id)
        if action:
            query = query.filter(SignatureAuditLog.action == action)
        if success is not None:
            query = query.filter(SignatureAuditLog.success.is_(success))
        if date_from:
            query = query.filter(SignatureAuditLog.timestamp >= date_from)
        if date_to:
            query = query.filter(SignatureAuditLog.timestamp <= date_to)
        return (
            query.order_by(SignatureAuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_audit_summary(
        self,
        *,
        item_id: Optional[str] = None,
        signature_id: Optional[str] = None,
        actor_id: Optional[int] = None,
        action: Optional[str] = None,
        success: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        filters = []
        if item_id:
            filters.append(SignatureAuditLog.item_id == item_id)
        if signature_id:
            filters.append(SignatureAuditLog.signature_id == signature_id)
        if actor_id is not None:
            filters.append(SignatureAuditLog.actor_id == actor_id)
        if action:
            filters.append(SignatureAuditLog.action == action)
        if success is not None:
            filters.append(SignatureAuditLog.success.is_(success))
        if date_from:
            filters.append(SignatureAuditLog.timestamp >= date_from)
        if date_to:
            filters.append(SignatureAuditLog.timestamp <= date_to)

        total = self.session.query(func.count(SignatureAuditLog.id)).filter(*filters).scalar()

        by_action = (
            self.session.query(SignatureAuditLog.action, func.count(SignatureAuditLog.id))
            .filter(*filters)
            .group_by(SignatureAuditLog.action)
            .all()
        )
        by_success = (
            self.session.query(SignatureAuditLog.success, func.count(SignatureAuditLog.id))
            .filter(*filters)
            .group_by(SignatureAuditLog.success)
            .all()
        )

        return {
            "total": int(total or 0),
            "by_action": {row[0]: int(row[1]) for row in by_action},
            "by_success": {str(row[0]).lower(): int(row[1]) for row in by_success},
        }

    def export_audit_logs(
        self,
        *,
        export_format: str,
        item_id: Optional[str] = None,
        signature_id: Optional[str] = None,
        actor_id: Optional[int] = None,
        action: Optional[str] = None,
        success: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 2000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        logs = self.list_audit_logs(
            item_id=item_id,
            signature_id=signature_id,
            actor_id=actor_id,
            action=action,
            success=success,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        normalized = export_format.lower().strip()
        rows = [
            {
                "id": log.id,
                "action": log.action,
                "signature_id": log.signature_id,
                "item_id": log.item_id,
                "actor_id": log.actor_id,
                "actor_username": log.actor_username,
                "details": log.details,
                "success": log.success,
                "error_message": log.error_message,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "client_ip": log.client_ip,
            }
            for log in logs
        ]

        if normalized == "json":
            payload = json.dumps({"items": rows}, ensure_ascii=False, default=str).encode(
                "utf-8"
            )
            return {"content": payload, "media_type": "application/json", "extension": "json"}

        if normalized != "csv":
            raise ValueError("Unsupported export format")

        columns = [
            "id",
            "action",
            "signature_id",
            "item_id",
            "actor_id",
            "actor_username",
            "details",
            "success",
            "error_message",
            "timestamp",
            "client_ip",
        ]
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(
                [
                    json.dumps(row.get(col), ensure_ascii=False)
                    if isinstance(row.get(col), (dict, list))
                    else ("" if row.get(col) is None else str(row.get(col)))
                    for col in columns
                ]
            )
        content = buffer.getvalue().encode("utf-8-sig")
        return {"content": content, "media_type": "text/csv", "extension": "csv"}
