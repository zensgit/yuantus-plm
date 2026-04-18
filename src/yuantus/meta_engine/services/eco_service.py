"""
ECO (Engineering Change Order) Service
Sprint 3: Complete ECO Change Management System

Key Features:
- ECO Lifecycle Management (Draft -> Progress -> Approved -> Done/Canceled)
- BOM Change Tracking (Add, Remove, Update)
- Rebase Conflict Detection: 3-way merge logic (Base vs Mine vs Theirs)
- ECO Application: Merges changes to the product's current version
- Approval Process integration (via ECOStageService and ECOApprovalService)
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.eco import (
    ECO,
    ECOBOMChange,
    ECOStage,
    ECOApproval,
    ECOState,
    ApprovalStatus,
)
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.version.service import VersionError, VersionService
from yuantus.meta_engine.version.file_service import VersionFileService, VersionFileError
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.services.audit_service import AuditService
from yuantus.meta_engine.services.notification_service import NotificationService
from yuantus.meta_engine.events.domain_events import (
    EcoCreatedEvent,
    EcoUpdatedEvent,
    EcoDeletedEvent,
)
from yuantus.meta_engine.events.transactional import enqueue_event
from yuantus.meta_engine.services.release_validation import ValidationIssue, get_release_ruleset
from yuantus.security.rbac.permissions import (
    PermissionManager as MetaPermissionService,
)
from yuantus.security.rbac.models import RBACUser


class ECOService:
    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)
        self.version_service = VersionService(session)
        self.permission_service = MetaPermissionService()  # Instantiate without session
        self.audit_service = AuditService(session)
        self.notification_service = NotificationService(session)

    def _resolve_actor_roles(self, user_id: Optional[int]) -> List[str]:
        if user_id is None:
            return []
        user = self.session.get(RBACUser, user_id)
        if not user:
            return []
        roles: List[str] = []
        for role in getattr(user, "roles", []) or []:
            name = str(getattr(role, "name", "") or "").strip().lower()
            if not name or name in roles:
                continue
            roles.append(name)
        return roles

    def _enqueue_eco_created(self, eco: ECO) -> None:
        enqueue_event(
            self.session,
            EcoCreatedEvent(
                eco_id=eco.id,
                eco_type=eco.eco_type,
                state=eco.state,
                product_id=eco.product_id,
            ),
        )

    def _enqueue_eco_updated(self, eco: ECO, changes: Optional[Dict[str, Any]] = None) -> None:
        enqueue_event(
            self.session,
            EcoUpdatedEvent(
                eco_id=eco.id,
                changes=changes or {},
                state=eco.state,
            ),
        )

    def _enqueue_eco_deleted(self, eco_id: str) -> None:
        enqueue_event(self.session, EcoDeletedEvent(eco_id=eco_id))

    def _resolve_stage_recipients(self, stage: Optional[ECOStage]) -> List[str]:
        if not stage:
            return []
        roles = stage.approval_roles or []
        if roles:
            return list(roles)
        return ["admin"]

    def _apply_stage_sla(self, eco: ECO, stage: Optional[ECOStage]) -> None:
        if not stage or stage.approval_type == "none":
            eco.approval_deadline = None
            return
        if stage.sla_hours is None:
            eco.approval_deadline = None
            return
        hours = max(int(stage.sla_hours), 0)
        eco.approval_deadline = datetime.utcnow() + timedelta(hours=hours)

    def _notify_stage_assignment(self, eco: ECO, stage: Optional[ECOStage]) -> None:
        if not stage:
            return
        recipients = self._resolve_stage_recipients(stage)
        self.notification_service.notify(
            "eco.stage_assigned",
            {
                "eco_id": eco.id,
                "stage_id": stage.id,
                "stage_name": stage.name,
                "approval_deadline": eco.approval_deadline.isoformat()
                if eco.approval_deadline
                else None,
            },
            recipients=recipients,
        )

    def _collect_apply_version_lock_issues(
        self,
        *,
        product: Item,
        target_version: ItemVersion,
        user_id: int,
        rule_id: str,
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        vf_service = VersionFileService(self.session)

        def _append_checkout_issue(version: ItemVersion, label: str) -> None:
            checked_out_by_id = getattr(version, "checked_out_by_id", None)
            if checked_out_by_id and checked_out_by_id != user_id:
                issues.append(
                    ValidationIssue(
                        code="eco_version_checked_out_by_another_user",
                        message=f"{label} {version.id} is checked out by another user ({checked_out_by_id})",
                        rule_id=rule_id,
                        details={"version_id": version.id, "owner_user_id": checked_out_by_id},
                    )
                )

        def _append_file_lock_issue(version: ItemVersion, label: str) -> None:
            blocking_locks = vf_service.get_blocking_file_locks(version.id, user_id=user_id)
            if not blocking_locks:
                return
            owners = sorted(
                {
                    str(vf.checked_out_by_id)
                    for vf in blocking_locks
                    if getattr(vf, "checked_out_by_id", None) is not None
                }
            )
            issues.append(
                ValidationIssue(
                    code="eco_version_file_locks_held_by_another_user",
                    message=(
                        f"{label} {version.id} has file-level locks held by another user"
                        + (f" ({', '.join(owners)})" if owners else "")
                    ),
                    rule_id=rule_id,
                    details={"version_id": version.id, "owner_user_ids": owners},
                )
            )

        if product.current_version_id and product.current_version_id != target_version.id:
            try:
                current_version = self.version_service.get_version(product.current_version_id)
            except VersionError:
                current_version = None
            if current_version:
                _append_checkout_issue(current_version, "Current version")
                _append_file_lock_issue(current_version, "Current version")

        _append_checkout_issue(target_version, "Target version")
        _append_file_lock_issue(target_version, "Target version")
        return issues

    def _ensure_activity_gate_ready(self, eco_id: str) -> None:
        """
        Block critical ECO transitions when activity gate reports unresolved blockers.
        """
        from yuantus.meta_engine.services.parallel_tasks_service import (
            ECOActivityValidationService,
        )

        blockers = ECOActivityValidationService(self.session).blockers_for_eco(eco_id)
        if int(blockers.get("total") or 0) <= 0:
            return

        blocker_ids = [
            str(entry.get("activity_id"))
            for entry in (blockers.get("blockers") or [])
            if entry.get("activity_id")
        ]
        joined = ", ".join(blocker_ids[:10])
        if len(blocker_ids) > 10:
            joined = f"{joined}, ..."
        raise ValueError(f"ECO activity blockers detected: {joined}")

    def _run_custom_actions(
        self,
        *,
        eco: ECO,
        from_state: Optional[str],
        to_state: Optional[str],
        trigger_phase: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Execute workflow custom actions bound to ECO state transition hooks.
        """
        from yuantus.meta_engine.services.parallel_tasks_service import (
            WorkflowCustomActionService,
        )

        runtime_context = {
            "source": "eco_service",
            "eco_id": eco.id,
            "stage_id": eco.stage_id,
            "eco_priority": (str(getattr(eco, "priority", "") or "").strip().lower() or None),
            "eco_type": (str(getattr(eco, "eco_type", "") or "").strip().lower() or None),
            "product_id": (str(getattr(eco, "product_id", "") or "").strip() or None),
            "workflow_map_id": (str(getattr(eco, "workflow_map_id", "") or "").strip() or None),
        }
        if context:
            runtime_context.update(dict(context))

        WorkflowCustomActionService(self.session).evaluate_transition(
            object_id=eco.id,
            target_object="ECO",
            from_state=from_state,
            to_state=to_state,
            trigger_phase=trigger_phase,
            context=runtime_context,
        )

    def _summarize_impact_scope(self, impact_count: int) -> str:
        if impact_count <= 0:
            return "isolated"
        if impact_count <= 3:
            return "localized"
        return "wide"

    def _summarize_bom_impact(self, bom_diff: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        summary = (bom_diff or {}).get("summary") or {}

        added = int(summary.get("added") or 0)
        removed = int(summary.get("removed") or 0)
        changed = int(summary.get("changed") or 0)
        changed_major = int(summary.get("changed_major") or 0)
        changed_minor = int(summary.get("changed_minor") or 0)
        changed_info = int(summary.get("changed_info") or 0)

        major_count = added + removed + changed_major
        minor_count = changed_minor
        info_count = changed_info

        if major_count > 0:
            level = "high"
        elif minor_count > 0:
            level = "medium"
        elif info_count > 0:
            level = "low"
        else:
            level = "none"

        score = major_count * 2 + minor_count * 1 + info_count * 0.5

        return {
            "summary": {
                "added": added,
                "removed": removed,
                "changed": changed,
                "changed_major": changed_major,
                "changed_minor": changed_minor,
                "changed_info": changed_info,
            },
            "level": level,
            "score": score,
        }

    def analyze_impact(
        self,
        eco_id: str,
        *,
        include_files: bool = False,
        include_bom_diff: bool = False,
        include_version_diff: bool = False,
        max_levels: int = 10,
        effective_at: Optional[datetime] = None,
        include_relationship_props: Optional[List[str]] = None,
        include_child_fields: bool = False,
        compare_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze the impact of an ECO.
        Identifies all assemblies and products that use the modified product.
        """
        eco = self.get_eco(eco_id)
        if not eco or not eco.product_id:
            raise ValueError(f"ECO {eco_id} not found or missing product")

        # Get recursive where-used for the product being modified
        # This tells us everything that depends on the product changing
        where_used = self.bom_service.get_where_used(eco.product_id, recursive=True)

        # Enrich data with Item details (optional, maybe where_used already has parent dict)
        # where_used returns list of dicts with 'parent' and 'relationship' keys

        bom_diff: Optional[Dict[str, Any]] = None
        if eco.source_version_id and eco.target_version_id:
            try:
                bom_diff = self.get_bom_diff(
                    eco_id,
                    max_levels=max_levels,
                    effective_at=effective_at,
                    include_relationship_props=include_relationship_props,
                    include_child_fields=include_child_fields,
                    compare_mode=compare_mode,
                )
            except ValueError:
                bom_diff = None

        bom_impact = self._summarize_bom_impact(bom_diff)
        impact_scope = self._summarize_impact_scope(len(where_used))

        result: Dict[str, Any] = {
            "eco_id": eco_id,
            "changed_product_id": eco.product_id,
            "impact_count": len(where_used),
            "impacted_assemblies": where_used,
            "impact_level": bom_impact["level"],
            "impact_score": bom_impact["score"],
            "impact_scope": impact_scope,
            "impact_summary": bom_impact["summary"],
        }
        if include_bom_diff and bom_diff:
            result["bom_diff"] = bom_diff
        if include_files:
            from yuantus.meta_engine.models.file import ItemFile
            from yuantus.meta_engine.version.models import VersionFile

            product = self.session.get(Item, eco.product_id)

            item_files = (
                self.session.query(ItemFile)
                .filter(ItemFile.item_id == eco.product_id)
                .order_by(ItemFile.sequence.asc())
                .all()
            )
            item_file_entries = [
                {
                    "attachment_id": f.id,
                    "file_id": f.file_id,
                    "file_role": f.file_role,
                    "sequence": f.sequence,
                    "filename": f.file.filename if f.file else None,
                    "file_type": f.file.file_type if f.file else None,
                    "file_size": f.file.file_size if f.file else None,
                }
                for f in item_files
            ]

            def load_version_files(version_id: Optional[str]) -> List[Dict[str, Any]]:
                if not version_id:
                    return []
                files = (
                    self.session.query(VersionFile)
                    .filter(VersionFile.version_id == version_id)
                    .order_by(VersionFile.sequence.asc())
                    .all()
                )
                return [
                    {
                        "id": vf.id,
                        "file_id": vf.file_id,
                        "file_role": vf.file_role,
                        "sequence": vf.sequence,
                        "is_primary": vf.is_primary,
                        "filename": vf.file.filename if vf.file else None,
                        "file_type": vf.file.file_type if vf.file else None,
                        "file_size": vf.file.file_size if vf.file else None,
                    }
                    for vf in files
                ]

            source_files = load_version_files(eco.source_version_id)
            target_files = load_version_files(eco.target_version_id)

            result["files"] = {
                "product_id": eco.product_id,
                "current_version_id": product.current_version_id if product else None,
                "item_files": item_file_entries,
                "source_version_files": source_files,
                "target_version_files": target_files,
            }
            result["files_summary"] = {
                "item_files": len(item_file_entries),
                "source_version_files": len(source_files),
                "target_version_files": len(target_files),
            }

        if include_version_diff:
            version_diff = None
            version_files_diff = None
            if eco.source_version_id and eco.target_version_id:
                try:
                    version_diff = self.version_service.compare_versions(
                        eco.source_version_id, eco.target_version_id
                    )
                except Exception:
                    version_diff = None
                try:
                    from yuantus.meta_engine.version.file_service import (
                        VersionFileService,
                    )

                    version_files_diff = VersionFileService(
                        self.session
                    ).compare_version_files(
                        eco.source_version_id, eco.target_version_id
                    )
                except Exception:
                    version_files_diff = None
            result["version_diff"] = version_diff
            result["version_files_diff"] = version_files_diff

        return result

    def _create_eco_bom_change(
        self,
        eco_id: str,
        change_type: str,
        relationship_item: Optional[Item],
        parent_item: Optional[Item],
        child_item: Optional[Item],
        old_properties: Optional[Dict[str, Any]],
        new_properties: Optional[Dict[str, Any]],
        conflict: bool = False,
        conflict_reason: Optional[str] = None,
    ) -> ECOBOMChange:
        """Helper to create an ECOBOMChange record."""
        bom_change = ECOBOMChange(
            id=str(uuid.uuid4()),
            eco_id=eco_id,
            change_type=change_type,
            relationship_item_id=relationship_item.id if relationship_item else None,
            parent_item_id=parent_item.id if parent_item else None,
            child_item_id=child_item.id if child_item else None,
            old_properties=old_properties,
            new_properties=new_properties,
            conflict=conflict,
            conflict_reason=conflict_reason,
        )
        self.session.add(bom_change)
        return bom_change

    def get_eco(self, eco_id: str) -> Optional[ECO]:
        return self.session.get(ECO, eco_id)

    def list_ecos(
        self,
        *,
        state: Optional[str] = None,
        stage_id: Optional[str] = None,
        product_id: Optional[str] = None,
        created_by_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ECO]:
        query = self.session.query(ECO)

        if state:
            query = query.filter(ECO.state == state)
        if stage_id:
            query = query.filter(ECO.stage_id == stage_id)
        if product_id:
            query = query.filter(ECO.product_id == product_id)
        if created_by_id is not None:
            query = query.filter(ECO.created_by_id == created_by_id)

        return (
            query.order_by(ECO.updated_at.desc(), ECO.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create_eco(
        self,
        name: str,
        eco_type: str,
        product_id: Optional[str],
        description: Optional[str] = None,
        priority: str = "normal",
        user_id: Optional[int] = 1,  # Default to TEST_USER_ID
        effectivity_date: Optional[datetime] = None,
    ) -> ECO:
        user_id_int = int(user_id) if user_id else 1

        if eco_type == "bom" and not product_id:
            raise ValueError("Missing product_id for bom ECO")

        # Permission check
        self.permission_service.check_permission(user_id_int, "create", "ECO")

        eco = ECO(
            id=str(uuid.uuid4()),
            name=name,
            eco_type=eco_type,
            product_id=product_id,
            description=description,
            priority=priority,
            created_by_id=user_id_int,
            effectivity_date=effectivity_date,
            state=ECOState.DRAFT.value,
            kanban_state="normal",
        )
        self.session.add(eco)
        self.session.flush()  # Assigns ID for relationships

        # Default stage: first by sequence (if configured)
        if not eco.stage_id:
            first_stage = (
                self.session.query(ECOStage).order_by(ECOStage.sequence.asc()).first()
            )
            if first_stage:
                eco.stage_id = first_stage.id
        if eco.stage_id:
            stage = self.session.get(ECOStage, eco.stage_id)
            if stage:
                self._apply_stage_sla(eco, stage)
                self._notify_stage_assignment(eco, stage)

        self._enqueue_eco_created(eco)
        return eco

    def update_eco(self, eco_id: str, updates: Dict[str, Any], user_id: int) -> ECO:
        # Permission check
        self.permission_service.check_permission(
            user_id, "update", "ECO", resource_id=eco_id
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO with ID {eco_id} not found.")

        for key, value in updates.items():
            setattr(eco, key, value)
        eco.updated_at = datetime.utcnow()
        self._enqueue_eco_updated(eco, changes=updates)
        return eco

    def delete_eco(self, eco_id: str, user_id: int):
        # Permission check
        self.permission_service.check_permission(
            user_id, "delete", "ECO", resource_id=eco_id
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO with ID {eco_id} not found.")
        self._enqueue_eco_deleted(eco.id)
        self.session.delete(eco)

    def move_to_stage(self, eco_id: str, stage_id: str, user_id: int) -> ECO:
        """
        Move ECO to a specific stage.
        Uses ECO's native stage system (ECOStage), not lifecycle states.
        """
        # Permission check
        self.permission_service.check_permission(
            user_id, "update", "ECO", resource_id=eco_id
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        if eco.state == ECOState.SUSPENDED.value:
            raise ValueError("ECO is suspended; unsuspend before moving stages")

        # Verify stage exists
        stage = self.session.query(ECOStage).get(stage_id)
        if not stage:
            raise ValueError(f"ECO Stage {stage_id} not found")

        self._ensure_activity_gate_ready(eco_id)
        from_state = eco.state
        to_state = (
            ECOState.PROGRESS.value if stage.approval_type != "none" else eco.state
        )
        self._run_custom_actions(
            eco=eco,
            from_state=from_state,
            to_state=to_state,
            trigger_phase="before",
            context={
                "stage_id": stage_id,
                "actor_roles": self._resolve_actor_roles(user_id),
            },
        )

        # Update ECO stage
        eco.stage_id = stage_id
        if stage.approval_type != "none":
            eco.state = ECOState.PROGRESS.value
        eco.updated_at = datetime.utcnow()
        self._apply_stage_sla(eco, stage)
        self._notify_stage_assignment(eco, stage)
        self.session.flush()

        self._enqueue_eco_updated(
            eco, changes={"stage_id": eco.stage_id, "state": eco.state}
        )
        self._run_custom_actions(
            eco=eco,
            from_state=from_state,
            to_state=eco.state,
            trigger_phase="after",
            context={
                "stage_id": eco.stage_id,
                "actor_roles": self._resolve_actor_roles(user_id),
            },
        )
        return eco

    def action_new_revision(self, eco_id: str, user_id: int):
        """
        Create a draft target version (branch) for the ECO's product and bind it to the ECO.
        """
        self.permission_service.check_permission(
            user_id, "execute", "ECO", resource_id=eco_id, field="new_revision"
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        if eco.state == ECOState.SUSPENDED.value:
            raise ValueError("ECO is suspended; unsuspend before creating a new revision")

        if not eco.product_id:
            raise ValueError("ECO is missing product_id")

        product = self.session.get(Item, eco.product_id)
        if not product:
            raise ValueError(f"Product with ID {eco.product_id} not found.")

        # Ensure the product has an initial version.
        if not product.current_version_id:
            self.version_service.create_initial_version(product, user_id)
            self.session.flush()

        source_version = self.session.get(ItemVersion, product.current_version_id)
        if not source_version:
            raise ValueError("Product current version not found")

        eco.source_version_id = source_version.id
        eco.product_version_before = source_version.version_label

        branch_name = f"eco-{eco.id[:8]}"
        target_version = self.version_service.create_branch(
            product.id, source_version.id, branch_name, user_id
        )
        self.session.flush()

        eco.target_version_id = target_version.id
        eco.product_version_after = target_version.version_label

        if eco.state == ECOState.DRAFT.value:
            eco.state = ECOState.PROGRESS.value
        eco.updated_at = datetime.utcnow()
        self.session.add(eco)

        self._enqueue_eco_updated(
            eco,
            changes={
                "source_version_id": eco.source_version_id,
                "target_version_id": eco.target_version_id,
                "state": eco.state,
            },
        )
        return target_version

    def action_suspend(self, eco_id: str, user_id: int, reason: Optional[str] = None) -> ECO:
        self.permission_service.check_permission(
            user_id, "execute", "ECO", resource_id=eco_id, field="suspend"
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        if eco.state == ECOState.SUSPENDED.value:
            raise ValueError("ECO is already suspended")
        if eco.state in {ECOState.DONE.value, ECOState.CANCELED.value}:
            raise ValueError(f"Cannot suspend ECO in {eco.state} state")

        from_state = eco.state
        runtime_context = {
            "reason": reason,
            "actor_roles": self._resolve_actor_roles(user_id),
        }
        self._run_custom_actions(
            eco=eco,
            from_state=from_state,
            to_state=ECOState.SUSPENDED.value,
            trigger_phase="before",
            context=runtime_context,
        )

        eco.state = ECOState.SUSPENDED.value
        eco.kanban_state = "blocked"
        eco.approval_deadline = None
        if reason:
            if eco.description:
                eco.description = f"{eco.description}\n\n[SUSPENDED] {reason}"
            else:
                eco.description = f"[SUSPENDED] {reason}"
        eco.updated_at = datetime.utcnow()
        self.session.add(eco)

        self._enqueue_eco_updated(
            eco,
            changes={"state": eco.state, "kanban_state": eco.kanban_state},
        )
        self._run_custom_actions(
            eco=eco,
            from_state=from_state,
            to_state=eco.state,
            trigger_phase="after",
            context=runtime_context,
        )
        return eco

    def action_unsuspend(
        self,
        eco_id: str,
        user_id: int,
        *,
        resume_state: Optional[str] = None,
    ) -> ECO:
        self.permission_service.check_permission(
            user_id, "execute", "ECO", resource_id=eco_id, field="unsuspend"
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        if eco.state != ECOState.SUSPENDED.value:
            raise ValueError("ECO is not suspended")

        normalized_resume_state = str(resume_state or ECOState.PROGRESS.value).strip().lower()
        allowed_resume_states = {
            ECOState.DRAFT.value,
            ECOState.PROGRESS.value,
            ECOState.CONFLICT.value,
            ECOState.APPROVED.value,
        }
        if normalized_resume_state not in allowed_resume_states:
            raise ValueError("resume_state must be one of: draft, progress, conflict, approved")

        stage = self.session.get(ECOStage, eco.stage_id) if eco.stage_id else None
        runtime_context = {
            "resume_state": normalized_resume_state,
            "actor_roles": self._resolve_actor_roles(user_id),
        }
        self._run_custom_actions(
            eco=eco,
            from_state=ECOState.SUSPENDED.value,
            to_state=normalized_resume_state,
            trigger_phase="before",
            context=runtime_context,
        )

        eco.state = normalized_resume_state
        eco.kanban_state = "normal"
        if normalized_resume_state == ECOState.APPROVED.value:
            eco.approval_deadline = None
        else:
            self._apply_stage_sla(eco, stage)
        eco.updated_at = datetime.utcnow()
        self.session.add(eco)

        self._enqueue_eco_updated(
            eco,
            changes={"state": eco.state, "kanban_state": eco.kanban_state},
        )
        self._run_custom_actions(
            eco=eco,
            from_state=ECOState.SUSPENDED.value,
            to_state=eco.state,
            trigger_phase="after",
            context=runtime_context,
        )
        return eco

    def get_unsuspend_diagnostics(
        self,
        eco_id: str,
        user_id: int,
        *,
        resume_state: Optional[str] = None,
        ruleset_id: str = "default",
    ) -> Dict[str, Any]:
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []

        eco = self.get_eco(eco_id)
        if not eco:
            errors.append(
                ValidationIssue(
                    code="eco_not_found",
                    message=f"ECO not found: {eco_id}",
                    rule_id="eco.exists",
                    details={"eco_id": eco_id},
                )
            )
            return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}

        normalized_resume_state = str(resume_state or ECOState.PROGRESS.value).strip().lower()
        allowed_resume_states = {
            ECOState.DRAFT.value,
            ECOState.PROGRESS.value,
            ECOState.CONFLICT.value,
            ECOState.APPROVED.value,
        }

        if eco.state != ECOState.SUSPENDED.value:
            errors.append(
                ValidationIssue(
                    code="eco_not_suspended",
                    message=f"ECO must be in '{ECOState.SUSPENDED.value}' state before unsuspending (current: {eco.state})",
                    rule_id="eco.state_suspended",
                    details={"eco_id": eco_id, "state": eco.state},
                )
            )
        if normalized_resume_state not in allowed_resume_states:
            errors.append(
                ValidationIssue(
                    code="eco_invalid_resume_state",
                    message="resume_state must be one of: draft, progress, conflict, approved",
                    rule_id="resume_state.allowed",
                    details={
                        "eco_id": eco_id,
                        "resume_state": normalized_resume_state,
                        "allowed": sorted(allowed_resume_states),
                    },
                )
            )

        stage = self.session.get(ECOStage, eco.stage_id) if eco.stage_id else None
        if eco.stage_id and not stage:
            errors.append(
                ValidationIssue(
                    code="eco_stage_not_found",
                    message=f"ECO stage not found: {eco.stage_id}",
                    rule_id="eco.stage_consistency",
                    details={"eco_id": eco_id, "stage_id": eco.stage_id},
                )
            )

        try:
            self._ensure_activity_gate_ready(eco_id)
        except ValueError as exc:
            errors.append(
                ValidationIssue(
                    code="eco_activity_blockers_present",
                    message=str(exc),
                    rule_id="eco.activity_blockers_clear",
                    details={"eco_id": eco_id},
                )
            )

        if (
            normalized_resume_state == ECOState.APPROVED.value
            and stage
            and stage.approval_type != "none"
            and not ECOApprovalService(self.session).check_stage_approvals_complete(eco_id, stage.id)
        ):
            errors.append(
                ValidationIssue(
                    code="eco_stage_approvals_incomplete",
                    message="Current stage approvals must be complete before resuming into approved state.",
                    rule_id="eco.approval_consistency",
                    details={
                        "eco_id": eco_id,
                        "stage_id": stage.id,
                        "resume_state": normalized_resume_state,
                    },
                )
            )

        return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}

    def can_unsuspend(
        self,
        eco_id: str,
        user_id: int,
        *,
        resume_state: Optional[str] = None,
        ruleset_id: str = "default",
    ) -> bool:
        diagnostics = self.get_unsuspend_diagnostics(
            eco_id,
            user_id,
            resume_state=resume_state,
            ruleset_id=ruleset_id,
        )
        return len(diagnostics.get("errors") or []) == 0

    def action_cancel(self, eco_id: str, user_id: int, reason: Optional[str] = None) -> ECO:
        self.permission_service.check_permission(
            user_id, "execute", "ECO", resource_id=eco_id, field="cancel"
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")

        eco.state = ECOState.CANCELED.value
        eco.kanban_state = "done"
        if reason:
            if eco.description:
                eco.description = f"{eco.description}\n\n[CANCELED] {reason}"
            else:
                eco.description = f"[CANCELED] {reason}"
        eco.updated_at = datetime.utcnow()
        self.session.add(eco)
        self._enqueue_eco_updated(eco, changes={"state": eco.state})
        return eco

    def get_bom_changes(self, eco_id: str) -> List[ECOBOMChange]:
        return (
            self.session.query(ECOBOMChange)
            .filter(ECOBOMChange.eco_id == eco_id)
            .order_by(ECOBOMChange.created_at.asc())
            .all()
        )

    def get_bom_diff(
        self,
        eco_id: str,
        *,
        max_levels: int = 10,
        effective_at: Optional[datetime] = None,
        include_relationship_props: Optional[List[str]] = None,
        include_child_fields: bool = False,
        compare_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute BOM redline diff between ECO source and target versions.
        """
        from yuantus.meta_engine.version.models import ItemVersion

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        if not eco.product_id:
            raise ValueError("ECO is missing product_id")
        if not eco.source_version_id or not eco.target_version_id:
            raise ValueError("ECO is missing source_version_id or target_version_id")

        source_version = self.session.get(ItemVersion, eco.source_version_id)
        target_version = self.session.get(ItemVersion, eco.target_version_id)
        if not source_version or not target_version:
            raise ValueError("ECO versions not found")

        def resolve_tree(version: ItemVersion) -> Dict[str, Any]:
            if effective_at:
                return self.bom_service.get_bom_structure(
                    version.item_id,
                    levels=max_levels,
                    effective_date=effective_at,
                )
            return self.bom_service.get_bom_for_version(version.id, levels=max_levels)

        def normalize_root(tree: Dict[str, Any]) -> Dict[str, Any]:
            if not tree:
                return tree
            normalized = dict(tree)
            normalized["config_id"] = "ROOT"
            return normalized

        left_tree = normalize_root(resolve_tree(source_version))
        right_tree = normalize_root(resolve_tree(target_version))

        aggregate_quantities = False
        line_key = "child_config"
        if compare_mode:
            line_key, include_relationship_props, aggregate_quantities = (
                self.bom_service.resolve_compare_mode(compare_mode)
            )

        diff = self.bom_service.compare_bom_trees(
            left_tree,
            right_tree,
            include_relationship_props=include_relationship_props,
            include_child_fields=include_child_fields,
            line_key=line_key,
            aggregate_quantities=aggregate_quantities,
        )
        diff.update(
            {
                "eco_id": eco_id,
                "source_version_id": eco.source_version_id,
                "target_version_id": eco.target_version_id,
                "compare_mode": compare_mode,
                "line_key": line_key,
            }
        )
        return diff

    def _flatten_level1_bom(
        self, bom_tree: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Flatten a level-1 BOM tree into:
          child_item_id -> {relationship_item_id, properties}
        """
        flattened: Dict[str, Dict[str, Any]] = {}
        for child_data in (bom_tree or {}).get("children", []) or []:
            child_item_id = ((child_data.get("child") or {}).get("id")) if child_data else None
            rel = child_data.get("relationship") if child_data else None
            if not child_item_id or not rel:
                continue
            flattened[str(child_item_id)] = {
                "relationship_item_id": rel.get("id"),
                "properties": rel.get("properties") or {},
            }
        return flattened

    def _create_eco_bom_change_from_compare_entry(
        self,
        *,
        eco_id: str,
        change_type: str,
        entry: Dict[str, Any],
    ) -> ECOBOMChange:
        relationship_id = entry.get("relationship_id")
        parent_id = entry.get("parent_id")
        child_id = entry.get("child_id")

        if change_type == "add":
            old_properties = None
            new_properties = entry.get("properties") or entry.get("after_line") or {}
        elif change_type == "remove":
            old_properties = entry.get("properties") or entry.get("before_line") or {}
            new_properties = None
        else:
            old_properties = entry.get("before_line") or entry.get("before") or {}
            new_properties = entry.get("after_line") or entry.get("after") or {}

        return self._create_eco_bom_change(
            eco_id=eco_id,
            change_type=change_type,
            relationship_item=self.session.get(Item, relationship_id) if relationship_id else None,
            parent_item=self.session.get(Item, parent_id) if parent_id else None,
            child_item=self.session.get(Item, child_id) if child_id else None,
            old_properties=old_properties,
            new_properties=new_properties,
        )

    def compute_bom_changes(self, eco_id: str, *, compare_mode: Optional[str] = None) -> List[ECOBOMChange]:
        """
        Compute BOM differences between source and target versions (level-1).
        Creates new ECOBOMChange rows (overwrites existing computed changes).
        """
        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        if not eco.product_id:
            raise ValueError("ECO is missing product_id")
        if not eco.source_version_id or not eco.target_version_id:
            raise ValueError("ECO is missing source_version_id or target_version_id")

        # Recompute: delete previous change rows
        self.session.query(ECOBOMChange).filter(ECOBOMChange.eco_id == eco_id).delete()
        self.session.flush()

        if compare_mode:
            diff = self.get_bom_diff(eco_id, max_levels=1, compare_mode=compare_mode)
            changes: List[ECOBOMChange] = []
            for entry in diff.get("added") or []:
                if isinstance(entry, dict):
                    changes.append(
                        self._create_eco_bom_change_from_compare_entry(
                            eco_id=eco_id,
                            change_type="add",
                            entry=entry,
                        )
                    )
            for entry in diff.get("removed") or []:
                if isinstance(entry, dict):
                    changes.append(
                        self._create_eco_bom_change_from_compare_entry(
                            eco_id=eco_id,
                            change_type="remove",
                            entry=entry,
                        )
                    )
            for entry in diff.get("changed") or []:
                if isinstance(entry, dict):
                    changes.append(
                        self._create_eco_bom_change_from_compare_entry(
                            eco_id=eco_id,
                            change_type="update",
                            entry=entry,
                        )
                    )
            self.session.flush()
            return changes

        base_tree = self.bom_service.get_bom_for_version(eco.source_version_id, levels=1)
        target_tree = self.bom_service.get_bom_for_version(eco.target_version_id, levels=1)

        base_flat = self._flatten_level1_bom(base_tree)
        target_flat = self._flatten_level1_bom(target_tree)

        all_child_ids = set(base_flat.keys()) | set(target_flat.keys())

        changes: List[ECOBOMChange] = []
        for child_id in sorted(all_child_ids):
            base_entry = base_flat.get(child_id)
            target_entry = target_flat.get(child_id)

            if base_entry is None and target_entry is not None:
                change = self._create_eco_bom_change(
                    eco_id=eco_id,
                    change_type="add",
                    relationship_item=None,
                    parent_item=self.session.get(Item, eco.product_id),
                    child_item=self.session.get(Item, child_id),
                    old_properties=None,
                    new_properties=target_entry.get("properties"),
                )
                changes.append(change)
                continue

            if base_entry is not None and target_entry is None:
                change = self._create_eco_bom_change(
                    eco_id=eco_id,
                    change_type="remove",
                    relationship_item=None,
                    parent_item=self.session.get(Item, eco.product_id),
                    child_item=self.session.get(Item, child_id),
                    old_properties=base_entry.get("properties"),
                    new_properties=None,
                )
                changes.append(change)
                continue

            if base_entry is None or target_entry is None:
                continue

            if (base_entry.get("properties") or {}) != (target_entry.get("properties") or {}):
                change = self._create_eco_bom_change(
                    eco_id=eco_id,
                    change_type="update",
                    relationship_item=None,
                    parent_item=self.session.get(Item, eco.product_id),
                    child_item=self.session.get(Item, child_id),
                    old_properties=base_entry.get("properties"),
                    new_properties=target_entry.get("properties"),
                )
                changes.append(change)

        self.session.flush()
        return changes

    def check_rebase_needed(self, eco_id: str) -> bool:
        """
        Check if the ECO needs a rebase.
        Rebase is needed if the product's current version has moved ahead of the ECO's source version.
        """
        eco = self.get_eco(eco_id)
        if not eco or not eco.product_id:
            return False

        product = self.session.get(Item, eco.product_id)
        if not product:
            return False
        # self.session.refresh(product) # Ensure product state is fresh - removed for now as per instructions
        if not product.current_version_id:
            return False

        # If ECO source version is not the same as product current version, we are behind
        print(
            f"DEBUG: check_rebase_needed: ECO Source={eco.source_version_id}, Product Current={product.current_version_id}"
        )
        return str(eco.source_version_id) != str(product.current_version_id)

    def detect_rebase_conflicts(self, eco_id: str) -> List[Dict[str, Any]]:
        """
        Detect conflicts between this ECO and the current product version.
        Returns a list of conflict details.
        """
        if not self.check_rebase_needed(eco_id):
            return []

        eco = self.get_eco(eco_id)
        if (
            not eco
            or not eco.product_id
            or not eco.source_version_id
            or not eco.target_version_id
        ):
            return []

        product = self.session.get(Item, eco.product_id)
        self.session.refresh(product)  # Ensure product state is fresh
        if not product or not product.current_version_id:
            return []

        # 1. Get 3 BOM snapshots
        # Base BOM: BOM as it was when the ECO was created (eco.source_version_id)
        # My BOM: BOM as modified by this ECO (eco.target_version_id)
        # Theirs BOM: Current BOM of the product (product.current_version_id)
        base_bom_tree = self.bom_service.get_bom_for_version(eco.source_version_id)
        my_bom_tree = self.bom_service.get_bom_for_version(eco.target_version_id)
        theirs_bom_tree = self.bom_service.get_bom_for_version(
            product.current_version_id
        )

        base_bom = self._flatten_bom_children(base_bom_tree)
        my_bom = self._flatten_bom_children(my_bom_tree)
        theirs_bom = self._flatten_bom_children(theirs_bom_tree)

        conflicts = []
        all_keys = set(base_bom.keys()) | set(my_bom.keys()) | set(theirs_bom.keys())

        for key in all_keys:
            base_val = base_bom.get(key)
            my_val = my_bom.get(key)
            theirs_val = theirs_bom.get(key)

            # Check for changes in My branch vs Base
            my_changed = base_val != my_val
            # Check for changes in Theirs branch vs Base
            theirs_changed = base_val != theirs_val

            if my_changed and theirs_changed and my_val != theirs_val:
                # Conflict: Both modified the same line, and their changes are different
                conflicts.append(
                    {
                        "child_item_id": key,
                        "base_value": base_val,
                        "my_value": my_val,
                        "their_value": theirs_val,
                        "reason": "concurrent_modification_different_values",
                    }
                )
            elif my_changed and not theirs_changed:
                # My change, no conflict with theirs (theirs didn't change from base)
                pass
            elif not my_changed and theirs_changed:
                # Their change, no conflict with mine (mine didn't change from base)
                pass
            elif my_changed and theirs_changed and my_val == theirs_val:
                # Both modified the same line in the same way (auto-merge, no conflict)
                pass

        return conflicts

    def _flatten_bom_children(self, bom_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flattens a BOM tree structure into a dictionary of child_item_id -> properties.
        Used for easier comparison in rebase conflict detection.
        """
        flattened = {}
        if not bom_tree or "children" not in bom_tree:
            return flattened

        for child_data in bom_tree["children"]:
            child_item_id = child_data["child"]["id"]

            # Key for comparison is child_item_id. Add position if available and important for uniqueness
            # For now, let's assume child_item_id is sufficient, properties will contain qty etc.
            key = child_item_id

            properties = child_data["relationship"]["properties"]
            # Add relevant properties to the flattened view for comparison
            # Deep copy to ensure modifications don't affect original
            flattened[key] = {**properties}

        return flattened

    def get_apply_diagnostics(
        self,
        eco_id: str,
        user_id: int,
        *,
        ruleset_id: str = "default",
        ignore_conflicts: bool = False,
    ) -> Dict[str, Any]:
        """
        Side-effect-free ECO apply diagnostics.

        Mirrors `action_apply` preconditions but returns structured errors/warnings.
        """
        rules = get_release_ruleset("eco_apply", ruleset_id)
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []

        eco = self.get_eco(eco_id)
        if not eco:
            errors.append(
                ValidationIssue(
                    code="eco_not_found",
                    message=f"ECO not found: {eco_id}",
                    rule_id="eco.exists",
                    details={"eco_id": eco_id},
                )
            )
            return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}

        # Keep parity with get_release_diagnostics patterns: evaluate configured rule ids.
        for rule in rules:
            if rule == "eco.exists":
                continue

            if rule == "eco.state_approved":
                if eco.state != ECOState.APPROVED.value:
                    errors.append(
                        ValidationIssue(
                            code="eco_not_approved",
                            message=(
                                f"ECO must be in '{ECOState.APPROVED.value}' state before applying "
                                f"(current: {eco.state})"
                            ),
                            rule_id=rule,
                            details={"eco_id": eco_id, "state": eco.state},
                        )
                    )

            elif rule == "eco.required_fields_present":
                missing: List[str] = []
                if not eco.product_id:
                    missing.append("product_id")
                if not eco.target_version_id:
                    missing.append("target_version_id")
                if missing:
                    errors.append(
                        ValidationIssue(
                            code="eco_missing_required_fields",
                            message=f"ECO is missing required fields: {', '.join(missing)}",
                            rule_id=rule,
                            details={"eco_id": eco_id, "missing": missing},
                        )
                    )

            elif rule == "eco.product_exists":
                if eco.product_id:
                    product = self.session.get(Item, eco.product_id)
                    if not product:
                        errors.append(
                            ValidationIssue(
                                code="eco_product_not_found",
                                message=f"Product not found: {eco.product_id}",
                                rule_id=rule,
                                details={"eco_id": eco_id, "product_id": eco.product_id},
                            )
                        )

            elif rule == "eco.target_version_exists":
                if eco.target_version_id:
                    try:
                        self.version_service.get_version(eco.target_version_id)
                    except VersionError:
                        errors.append(
                            ValidationIssue(
                                code="eco_target_version_not_found",
                                message=f"Target version not found: {eco.target_version_id}",
                                rule_id=rule,
                                details={
                                    "eco_id": eco_id,
                                    "target_version_id": eco.target_version_id,
                                },
                            )
                        )

            elif rule == "eco.version_locks_clear":
                if eco.product_id and eco.target_version_id:
                    product = self.session.get(Item, eco.product_id)
                    if product:
                        try:
                            target_version = self.version_service.get_version(eco.target_version_id)
                        except VersionError:
                            target_version = None
                        if target_version:
                            errors.extend(
                                self._collect_apply_version_lock_issues(
                                    product=product,
                                    target_version=target_version,
                                    user_id=user_id,
                                    rule_id=rule,
                                )
                            )

            elif rule == "eco.rebase_conflicts_absent":
                if ignore_conflicts:
                    continue
                try:
                    has_conflicts = bool(
                        self.check_rebase_needed(eco_id) and self.detect_rebase_conflicts(eco_id)
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    warnings.append(
                        ValidationIssue(
                            code="eco_rebase_check_failed",
                            message=f"Rebase conflict check failed: {exc}",
                            rule_id=rule,
                            details={"eco_id": eco_id},
                        )
                    )
                    continue
                if has_conflicts:
                    errors.append(
                        ValidationIssue(
                            code="eco_rebase_conflicts",
                            message="Rebase conflicts detected. Resolve conflicts before applying ECO.",
                            rule_id=rule,
                            details={"eco_id": eco_id},
                        )
                    )

        return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}

    def action_apply(self, eco_id: str, user_id: int, *, ignore_conflicts: bool = False) -> bool:
        # Permission check
        self.permission_service.check_permission(
            user_id, "execute", "ECO", resource_id=eco_id, field="apply"
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO with ID {eco_id} not found.")

        if eco.state != ECOState.APPROVED.value:
            raise ValueError(
                f"ECO must be in '{ECOState.APPROVED.value}' state before applying (current: {eco.state})"
            )

        if not eco.product_id or not eco.target_version_id:
            raise ValueError(
                "ECO is missing product_id or target_version_id for application."
            )

        self._ensure_activity_gate_ready(eco_id)
        from_state = eco.state
        self._run_custom_actions(
            eco=eco,
            from_state=from_state,
            to_state=ECOState.DONE.value,
            trigger_phase="before",
            context={"actor_roles": self._resolve_actor_roles(user_id)},
        )

        # If rebase is needed, it must be resolved manually (i.e., conflicts list should be empty)
        if (
            not ignore_conflicts
            and self.check_rebase_needed(eco_id)
            and self.detect_rebase_conflicts(eco_id)
        ):
            raise ValueError(
                "Rebase conflicts detected. Resolve conflicts before applying ECO."
            )

        product = self.session.get(Item, eco.product_id)
        if not product:
            raise ValueError(f"Product with ID {eco.product_id} not found.")

        target_version = self.version_service.get_version(eco.target_version_id)
        lock_issues = self._collect_apply_version_lock_issues(
            product=product,
            target_version=target_version,
            user_id=user_id,
            rule_id="eco.version_locks_clear",
        )
        if lock_issues:
            raise ValueError(lock_issues[0].message)

        # Switch current pointer + flags (best-effort)
        if product.current_version_id and product.current_version_id != target_version.id:
            try:
                current_version = self.version_service.get_version(product.current_version_id)
                current_version.is_current = False
                self.session.add(current_version)
            except Exception:
                # If the current version row is missing, continue with apply.
                pass

        target_version.is_current = True
        self.session.add(target_version)

        product.current_version_id = target_version.id
        if target_version.properties is not None:
            product.properties = dict(target_version.properties)
        product.updated_at = datetime.utcnow()
        self.session.add(product)

        try:
            VersionFileService(self.session).sync_version_files_to_item(
                version_id=target_version.id,
                item_id=product.id,
                user_id=user_id,
                remove_missing=True,
            )
        except VersionFileError as exc:
            raise ValueError(str(exc)) from exc

        eco.state = ECOState.DONE.value
        eco.kanban_state = "done"
        eco.product_version_after = target_version.version_label
        eco.updated_at = datetime.utcnow()
        self.session.add(eco)

        self._enqueue_eco_updated(
            eco,
            changes={
                "state": eco.state,
                "product_version_after": eco.product_version_after,
            },
        )
        self._run_custom_actions(
            eco=eco,
            from_state=from_state,
            to_state=eco.state,
            trigger_phase="after",
            context={"actor_roles": self._resolve_actor_roles(user_id)},
        )
        return True


class ECOStageService:
    def __init__(self, session: Session):
        self.session = session
        self.permission_service = MetaPermissionService()  # Instantiate without session

    def get_stage(self, stage_id: str) -> Optional[ECOStage]:
        return self.session.get(ECOStage, stage_id)

    def get_stage_by_name(self, name: str) -> Optional[ECOStage]:
        return self.session.query(ECOStage).filter_by(name=name).first()

    def list_stages(self) -> List[ECOStage]:
        return self.session.query(ECOStage).order_by(ECOStage.sequence).all()

    def create_stage(
        self,
        name: str,
        sequence: Optional[int] = None,
        approval_type: str = "none",
        approval_roles: Optional[List[str]] = None,
        min_approvals: int = 1,
        is_blocking: bool = False,
        fold: bool = False,
        auto_progress: bool = False,
        sla_hours: Optional[int] = None,
        description: Optional[str] = None,
        user_id: int = 1,  # Default to TEST_USER_ID
    ) -> ECOStage:
        self.permission_service.check_permission(user_id, "create", "ECOStage")

        if sequence is None:
            last = self.session.query(ECOStage).order_by(ECOStage.sequence.desc()).first()
            sequence = (last.sequence + 10) if last and last.sequence is not None else 10

        stage = ECOStage(
            id=str(uuid.uuid4()),
            name=name,
            sequence=sequence,
            approval_type=approval_type,
            approval_roles=approval_roles,
            min_approvals=min_approvals,
            is_blocking=is_blocking,
            fold=fold,
            auto_progress=auto_progress,
            sla_hours=sla_hours,
            description=description,
        )
        self.session.add(stage)
        self.session.flush()
        return stage

    def update_stage(self, stage_id: str, **updates: Any) -> ECOStage:
        stage = self.get_stage(stage_id)
        if not stage:
            raise ValueError(f"Stage {stage_id} not found")

        allowed_fields = {
            "name",
            "sequence",
            "approval_type",
            "approval_roles",
            "min_approvals",
            "is_blocking",
            "fold",
            "auto_progress",
            "sla_hours",
            "description",
        }
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(stage, key, value)

        self.session.add(stage)
        self.session.flush()
        return stage

    def delete_stage(self, stage_id: str) -> bool:
        stage = self.get_stage(stage_id)
        if not stage:
            return False

        in_use = self.session.query(ECO).filter(ECO.stage_id == stage_id).count()
        if in_use > 0:
            raise ValueError("Cannot delete stage: stage is in use by ECOs")

        self.session.delete(stage)
        self.session.flush()
        return True


class ECOApprovalService:
    def __init__(self, session: Session):
        self.session = session
        self.permission_service = MetaPermissionService()  # Instantiate without session
        self.audit_service = AuditService(session)
        self.notification_service = NotificationService(session)

    def _enqueue_eco_updated(self, eco: ECO, changes: Optional[Dict[str, Any]] = None) -> None:
        enqueue_event(
            self.session,
            EcoUpdatedEvent(
                eco_id=eco.id,
                changes=changes or {},
                state=eco.state,
            ),
        )

    def _resolve_stage_recipients(self, stage: Optional[ECOStage]) -> List[str]:
        if not stage:
            return []
        roles = stage.approval_roles or []
        if roles:
            return list(roles)
        return ["admin"]

    def _apply_stage_sla(self, eco: ECO, stage: Optional[ECOStage]) -> None:
        if not stage or stage.approval_type == "none":
            eco.approval_deadline = None
            return
        if stage.sla_hours is None:
            eco.approval_deadline = None
            return
        hours = max(int(stage.sla_hours), 0)
        eco.approval_deadline = datetime.utcnow() + timedelta(hours=hours)

    def get_approval(self, approval_id: str) -> Optional[ECOApproval]:
        return self.session.get(ECOApproval, approval_id)

    def list_approvals_for_eco(self, eco_id: str) -> List[ECOApproval]:
        return self.session.query(ECOApproval).filter_by(eco_id=eco_id).all()

    def get_eco_approvals(self, eco_id: str) -> List[ECOApproval]:
        return self.list_approvals_for_eco(eco_id)

    def _resolve_stage_candidate_users(self, stage: ECOStage) -> List[Dict[str, Any]]:
        roles = [
            str(role).strip()
            for role in (stage.approval_roles or [])
            if str(role).strip()
        ]
        if not roles:
            return []

        candidates: List[Dict[str, Any]] = []
        seen_user_ids = set()
        users = self.session.query(RBACUser).all()
        for user in users:
            user_id = getattr(user, "id", None)
            if user_id in seen_user_ids:
                continue
            if getattr(user, "is_active", True) is False:
                continue

            matched_roles = sorted(
                {
                    str(getattr(role, "name", "")).strip()
                    for role in (getattr(user, "roles", None) or [])
                    if getattr(role, "is_active", True) is not False
                    and str(getattr(role, "name", "")).strip() in roles
                }
            )
            if not matched_roles:
                continue

            seen_user_ids.add(user_id)
            candidates.append(
                {
                    "user_id": user_id,
                    "username": getattr(user, "username", None),
                    "email": getattr(user, "email", None),
                    "matched_roles": matched_roles,
                }
            )

        candidates.sort(
            key=lambda row: (
                str(row.get("username") or ""),
                int(row.get("user_id") or 0),
            )
        )
        return candidates

    def get_approval_routing(self, eco_id: str) -> Dict[str, Any]:
        eco = self.session.get(ECO, eco_id)
        if not eco:
            raise ValueError("ECO not found")

        stage = self.session.get(ECOStage, eco.stage_id) if eco.stage_id else None
        if not stage:
            return {
                "eco_id": eco.id,
                "eco_state": eco.state,
                "stage_id": eco.stage_id,
                "stage_name": None,
                "approval_type": "none",
                "approval_roles": [],
                "min_approvals": 0,
                "approval_deadline": eco.approval_deadline.isoformat()
                if eco.approval_deadline
                else None,
                "is_overdue": False,
                "routing_mode": "none",
                "routing_ready": False,
                "routing_gap": "ECO has no stage assigned",
                "candidate_approvers": [],
                "candidate_approver_count": 0,
                "approvals": [],
                "approved_count": 0,
                "rejected_count": 0,
                "remaining_required": 0,
                "stage_complete": False,
            }

        approvals = (
            self.session.query(ECOApproval)
            .filter_by(eco_id=eco.id, stage_id=stage.id)
            .all()
        )
        approval_rows: List[Dict[str, Any]] = []
        latest_by_user: Dict[int, ECOApproval] = {}
        approved_count = 0
        rejected_count = 0
        for approval in approvals:
            if (
                approval.status == ApprovalStatus.APPROVED.value
                and approval.approval_type == "mandatory"
            ):
                approved_count += 1
            if approval.status == ApprovalStatus.REJECTED.value:
                rejected_count += 1

            if approval.user_id is not None:
                current = latest_by_user.get(approval.user_id)
                current_ts = getattr(current, "approved_at", None) or getattr(
                    current, "created_at", None
                )
                approval_ts = getattr(approval, "approved_at", None) or getattr(
                    approval, "created_at", None
                )
                if current is None or (
                    approval_ts is not None
                    and (current_ts is None or approval_ts >= current_ts)
                ):
                    latest_by_user[approval.user_id] = approval

            approval_rows.append(
                {
                    "approval_id": approval.id,
                    "user_id": approval.user_id,
                    "status": approval.status,
                    "approval_type": approval.approval_type,
                    "required_role": approval.required_role,
                    "comment": approval.comment,
                    "approved_at": approval.approved_at.isoformat()
                    if approval.approved_at
                    else None,
                    "created_at": approval.created_at.isoformat()
                    if approval.created_at
                    else None,
                }
            )

        stage_complete = self.check_stage_approvals_complete(eco.id, stage.id)
        remaining_required = max(int(stage.min_approvals or 0) - approved_count, 0)
        deadline = eco.approval_deadline
        is_overdue = bool(deadline and deadline <= datetime.utcnow())

        candidate_approvers = self._resolve_stage_candidate_users(stage)
        for candidate in candidate_approvers:
            latest = latest_by_user.get(candidate["user_id"])
            candidate["decision_status"] = (
                latest.status if latest else ApprovalStatus.PENDING.value
            )
            candidate["approval_id"] = latest.id if latest else None

        if stage.approval_type == "none":
            routing_mode = "none"
            routing_ready = True
            routing_gap = None
        elif stage.approval_roles:
            routing_mode = "role_based"
            routing_ready = True
            routing_gap = None
        else:
            routing_mode = "open"
            routing_ready = False
            routing_gap = (
                "Stage approval_roles not configured; approvals are not explicitly routed"
            )

        return {
            "eco_id": eco.id,
            "eco_state": eco.state,
            "stage_id": stage.id,
            "stage_name": stage.name,
            "approval_type": stage.approval_type,
            "approval_roles": list(stage.approval_roles or []),
            "min_approvals": int(stage.min_approvals or 0),
            "approval_deadline": deadline.isoformat() if deadline else None,
            "is_overdue": is_overdue,
            "routing_mode": routing_mode,
            "routing_ready": routing_ready,
            "routing_gap": routing_gap,
            "candidate_approvers": candidate_approvers,
            "candidate_approver_count": len(candidate_approvers),
            "approvals": approval_rows,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "remaining_required": remaining_required,
            "stage_complete": stage_complete,
        }

    def _user_has_stage_role(self, user: Optional[RBACUser], stage: ECOStage) -> bool:
        if not stage.approval_roles:
            return True
        if not user:
            return False
        if user.is_superuser:
            return True
        # Only consider active roles
        user_role_names = {
            r.name for r in (user.roles or [])
            if getattr(r, "is_active", True)
        }
        return any(role_name in user_role_names for role_name in (stage.approval_roles or []))

    def get_pending_approvals(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Return a computed list of pending approvals for the given user.

        NOTE: We don't pre-create ECOApproval rows for every user/stage. Instead we
        compute "pending" based on ECO.stage + user roles and existing approval records.
        """
        user = self.session.query(RBACUser).filter(RBACUser.id == user_id).first()

        now = datetime.utcnow()
        ecos = (
            self.session.query(ECO)
            .filter(ECO.state.in_([ECOState.DRAFT.value, ECOState.PROGRESS.value]))
            .filter(ECO.stage_id.isnot(None))
            .order_by(ECO.updated_at.desc(), ECO.created_at.desc())
            .all()
        )

        pending: List[Dict[str, Any]] = []
        for eco in ecos:
            stage = self.session.get(ECOStage, eco.stage_id) if eco.stage_id else None
            if not stage:
                continue
            if stage.approval_type == "none":
                continue
            if not self._user_has_stage_role(user, stage):
                continue

            already = (
                self.session.query(ECOApproval)
                .filter_by(eco_id=eco.id, stage_id=stage.id, user_id=user_id)
                .filter(ECOApproval.status.in_([ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value]))
                .first()
            )
            if already:
                continue

            deadline = eco.approval_deadline
            is_overdue = bool(deadline and deadline <= now)
            hours_left = None
            if deadline:
                hours_left = (deadline - now).total_seconds() / 3600

            pending.append(
                {
                    "eco_id": eco.id,
                    "eco_name": eco.name,
                    "eco_state": eco.state,
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "approval_type": stage.approval_type,
                    "approval_deadline": deadline.isoformat() if deadline else None,
                    "is_overdue": is_overdue,
                    "hours_left": hours_left,
                }
            )

        return pending

    def list_overdue_approvals(self, as_of: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = as_of or datetime.utcnow()
        ecos = (
            self.session.query(ECO)
            .filter(ECO.state.in_([ECOState.DRAFT.value, ECOState.PROGRESS.value]))
            .filter(ECO.stage_id.isnot(None))
            .filter(ECO.approval_deadline.isnot(None))
            .order_by(ECO.approval_deadline.asc())
            .all()
        )

        overdue: List[Dict[str, Any]] = []
        for eco in ecos:
            if not eco.approval_deadline or eco.approval_deadline > now:
                continue
            stage = self.session.get(ECOStage, eco.stage_id) if eco.stage_id else None
            recipients = self._resolve_stage_recipients(stage)
            hours_overdue = (now - eco.approval_deadline).total_seconds() / 3600
            overdue.append(
                {
                    "eco_id": eco.id,
                    "eco_name": eco.name,
                    "stage_id": stage.id if stage else None,
                    "stage_name": stage.name if stage else None,
                    "approval_deadline": eco.approval_deadline.isoformat(),
                    "hours_overdue": hours_overdue,
                    "recipients": recipients,
                }
            )
        return overdue

    # ------------------------------------------------------------------
    # P2-3: Approval Dashboard
    # ------------------------------------------------------------------

    def _base_dashboard_query(
        self,
        *,
        company_id: Optional[str] = None,
        eco_type: Optional[str] = None,
        eco_state: Optional[str] = None,
        deadline_from: Optional[datetime] = None,
        deadline_to: Optional[datetime] = None,
    ):
        """Canonical base query for both summary and items.

        Joins: ECO → ECOStage (current) → ECOApproval (same stage only).
        Filters: active ECO + approval_type != none + pending approval +
                 approval bound to ECO's *current* stage.

        Optional filters (P2-3.1 PR-1):
            company_id, eco_type (category), eco_state, deadline window.
        """
        states = [ECOState.DRAFT.value, ECOState.PROGRESS.value]
        if eco_state:
            states = [eco_state]

        query = (
            self.session.query(ECO, ECOStage, ECOApproval)
            .join(ECOStage, ECO.stage_id == ECOStage.id)
            .join(ECOApproval, (
                (ECOApproval.eco_id == ECO.id)
                & (ECOApproval.stage_id == ECO.stage_id)
            ))
            .filter(
                ECO.state.in_(states),
                ECOStage.approval_type != "none",
                ECOApproval.status == "pending",
            )
        )

        if company_id:
            query = query.filter(ECO.company_id == company_id)
        if eco_type:
            query = query.filter(ECO.eco_type == eco_type)
        if deadline_from:
            query = query.filter(ECO.approval_deadline >= deadline_from)
        if deadline_to:
            query = query.filter(ECO.approval_deadline <= deadline_to)

        return query

    def get_approval_dashboard_summary(
        self,
        *,
        company_id: Optional[str] = None,
        eco_type: Optional[str] = None,
        eco_state: Optional[str] = None,
        deadline_from: Optional[datetime] = None,
        deadline_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Aggregate counts from the same base query as items."""
        now = datetime.utcnow()
        rows = self._base_dashboard_query(
            company_id=company_id, eco_type=eco_type, eco_state=eco_state,
            deadline_from=deadline_from, deadline_to=deadline_to,
        ).all()

        pending_count = 0
        overdue_count = 0
        escalated_count = 0
        by_stage: Dict[str, Dict[str, Any]] = {}
        by_role: Dict[str, int] = {}
        by_assignee_map: Dict[int, Dict[str, Any]] = {}

        for eco, stage, approval in rows:
            is_overdue = bool(eco.approval_deadline and eco.approval_deadline <= now)
            is_escalated = approval.required_role == "admin"

            if is_overdue:
                overdue_count += 1
            else:
                pending_count += 1
            if is_escalated:
                escalated_count += 1

            sk = stage.id
            if sk not in by_stage:
                by_stage[sk] = {"stage_id": sk, "stage_name": stage.name, "pending": 0, "overdue": 0}
            if is_overdue:
                by_stage[sk]["overdue"] += 1
            else:
                by_stage[sk]["pending"] += 1

            for role in (stage.approval_roles or []):
                by_role[role] = by_role.get(role, 0) + 1

            uid = approval.user_id
            if uid not in by_assignee_map:
                user = self.session.get(RBACUser, uid)
                by_assignee_map[uid] = {
                    "user_id": uid,
                    "username": user.username if user else str(uid),
                    "pending_count": 0,
                }
            by_assignee_map[uid]["pending_count"] += 1

        return {
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "escalated_count": escalated_count,
            "by_stage": list(by_stage.values()),
            "by_role": [{"role": r, "count": c} for r, c in sorted(by_role.items())],
            "by_assignee": sorted(by_assignee_map.values(), key=lambda x: -x["pending_count"]),
        }

    def get_approval_dashboard_items(
        self,
        *,
        status_filter: Optional[str] = None,
        stage_id: Optional[str] = None,
        assignee_id: Optional[int] = None,
        role: Optional[str] = None,
        company_id: Optional[str] = None,
        eco_type: Optional[str] = None,
        eco_state: Optional[str] = None,
        deadline_from: Optional[datetime] = None,
        deadline_to: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Filtered items from the same base query as summary."""
        now = datetime.utcnow()
        query = self._base_dashboard_query(
            company_id=company_id, eco_type=eco_type, eco_state=eco_state,
            deadline_from=deadline_from, deadline_to=deadline_to,
        )

        if stage_id:
            query = query.filter(ECOStage.id == stage_id)
        if assignee_id:
            query = query.filter(ECOApproval.user_id == assignee_id)
        if role:
            query = query.filter(ECOStage.approval_roles.contains([role]))

        if status_filter == "overdue":
            query = query.filter(
                ECO.approval_deadline.isnot(None),
                ECO.approval_deadline <= now,
            )
        elif status_filter == "escalated":
            query = query.filter(ECOApproval.required_role == "admin")
        elif status_filter == "pending":
            query = query.filter(
                ECO.approval_deadline.is_(None)
                | (ECO.approval_deadline > now)
            )

        rows = query.order_by(ECO.approval_deadline.asc().nullslast()).limit(limit).all()

        items = []
        for eco, stage, approval in rows:
            is_overdue = bool(eco.approval_deadline and eco.approval_deadline <= now)
            user = self.session.get(RBACUser, approval.user_id)
            items.append({
                "eco_id": eco.id,
                "eco_name": eco.name,
                "eco_state": eco.state,
                "stage_id": stage.id,
                "stage_name": stage.name,
                "approval_id": approval.id,
                "assignee_id": approval.user_id,
                "assignee_username": user.username if user else str(approval.user_id),
                "approval_type": approval.approval_type,
                "required_role": approval.required_role,
                "is_overdue": is_overdue,
                "is_escalated": approval.required_role == "admin",
                "approval_deadline": (
                    eco.approval_deadline.isoformat() if eco.approval_deadline else None
                ),
                "hours_overdue": (
                    (now - eco.approval_deadline).total_seconds() / 3600
                    if is_overdue else None
                ),
            })
        return items

    # ------------------------------------------------------------------
    # P2-3.1 PR-2: Dashboard Export
    # ------------------------------------------------------------------

    _EXPORT_COLUMNS = [
        "eco_id", "eco_name", "eco_state", "stage_id", "stage_name",
        "approval_id", "assignee_id", "assignee_username",
        "approval_type", "required_role", "is_overdue", "is_escalated",
        "approval_deadline", "hours_overdue",
    ]

    def export_dashboard_items(
        self,
        fmt: str = "json",
        **filter_kwargs,
    ) -> str:
        """Export dashboard items as JSON or CSV string.

        Uses the same ``get_approval_dashboard_items`` query — no second口径.
        """
        items = self.get_approval_dashboard_items(**filter_kwargs)

        if fmt == "csv":
            import csv
            import io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=self._EXPORT_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow(item)
            return buf.getvalue()

        # default: json
        import json
        return json.dumps(items, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------
    # P2-3.1 PR-3: Approval Ops Audit
    # ------------------------------------------------------------------

    def get_approval_anomalies(self) -> Dict[str, Any]:
        """Lightweight anomaly report for operations.

        Returns three categories of stuck approvals:
        - no_candidates: stages needing approval but 0 eligible users
        - escalated_unresolved: admin-escalated approvals still pending
        - overdue_not_escalated: overdue but not yet escalated
        """
        now = datetime.utcnow()

        # Active ECOs with approval stages
        ecos_with_stages = (
            self.session.query(ECO, ECOStage)
            .join(ECOStage, ECO.stage_id == ECOStage.id)
            .filter(
                ECO.state.in_([ECOState.DRAFT.value, ECOState.PROGRESS.value]),
                ECOStage.approval_type != "none",
            )
            .all()
        )

        no_candidates = []
        for eco, stage in ecos_with_stages:
            candidates = self._resolve_candidate_users(stage)
            if not candidates:
                no_candidates.append({
                    "eco_id": eco.id,
                    "eco_name": eco.name,
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "approval_roles": stage.approval_roles,
                    "reason": "no active users with matching active roles",
                })

        # Escalated but still pending
        escalated_unresolved = []
        esc_rows = (
            self.session.query(ECOApproval, ECO, ECOStage)
            .join(ECO, ECOApproval.eco_id == ECO.id)
            .join(ECOStage, ECOApproval.stage_id == ECOStage.id)
            .filter(
                ECOApproval.required_role == "admin",
                ECOApproval.status == "pending",
                ECOApproval.stage_id == ECO.stage_id,  # current stage only
                ECO.state.in_([ECOState.DRAFT.value, ECOState.PROGRESS.value]),
            )
            .all()
        )
        for appr, eco, stage in esc_rows:
            user = self.session.get(RBACUser, appr.user_id)
            escalated_unresolved.append({
                "eco_id": eco.id,
                "eco_name": eco.name,
                "stage_id": stage.id,
                "stage_name": stage.name,
                "admin_user_id": appr.user_id,
                "admin_username": user.username if user else str(appr.user_id),
                "approval_id": appr.id,
            })

        # Overdue but not yet escalated (no admin approval exists)
        overdue_not_escalated = []
        overdue_ecos = self.list_overdue_approvals()
        for entry in overdue_ecos:
            eco_id = entry["eco_id"]
            stage_id = entry.get("stage_id")
            if not stage_id:
                continue
            has_admin = (
                self.session.query(ECOApproval)
                .filter_by(eco_id=eco_id, stage_id=stage_id, required_role="admin")
                .first()
            )
            if not has_admin:
                overdue_not_escalated.append({
                    "eco_id": eco_id,
                    "eco_name": entry.get("eco_name"),
                    "stage_id": stage_id,
                    "stage_name": entry.get("stage_name"),
                    "hours_overdue": entry.get("hours_overdue"),
                    "reason": "overdue but no escalation triggered",
                })

        return {
            "no_candidates": no_candidates,
            "escalated_unresolved": escalated_unresolved,
            "overdue_not_escalated": overdue_not_escalated,
            "total_anomalies": (
                len(no_candidates)
                + len(escalated_unresolved)
                + len(overdue_not_escalated)
            ),
        }

    def notify_overdue_approvals(self) -> Dict[str, Any]:
        overdue = self.list_overdue_approvals()
        notified = 0
        for entry in overdue:
            self.notification_service.notify(
                "eco.approval_overdue",
                {
                    "eco_id": entry["eco_id"],
                    "stage_id": entry["stage_id"],
                    "approval_deadline": entry["approval_deadline"],
                    "hours_overdue": entry["hours_overdue"],
                },
                recipients=entry.get("recipients") or [],
            )
            notified += 1
        return {"count": len(overdue), "notified": notified, "items": overdue}

    def approve(self, eco_id: str, user_id: int, comment: Optional[str] = None) -> ECOApproval:
        eco = self.session.get(ECO, eco_id)
        if not eco:
            raise ValueError("ECO not found")
        if eco.state == ECOState.SUSPENDED.value:
            raise ValueError("ECO is suspended; unsuspend before approving")
        if not eco.stage_id:
            raise ValueError("ECO has no stage assigned")

        stage = self.session.get(ECOStage, eco.stage_id)
        if not stage:
            raise ValueError("ECO stage not found")

        user = self.session.query(RBACUser).filter(RBACUser.id == user_id).first()
        if not self._user_has_stage_role(user, stage):
            raise ValueError("User does not have approval role for this stage")

        approval = (
            self.session.query(ECOApproval)
            .filter_by(eco_id=eco_id, stage_id=stage.id, user_id=user_id)
            .first()
        )
        if not approval:
            approval = ECOApproval(
                id=str(uuid.uuid4()),
                eco_id=eco_id,
                stage_id=stage.id,
                user_id=user_id,
                approval_type="mandatory",
                required_role=None,
                status=ApprovalStatus.PENDING.value,
                comment=None,
            )
            self.session.add(approval)

        approval.status = ApprovalStatus.APPROVED.value
        approval.comment = comment
        approval.approved_at = datetime.utcnow()
        self.session.add(approval)
        self.session.flush()

        stage_complete = False
        # If this stage is complete, progress ECO
        if self.check_stage_approvals_complete(eco_id, stage.id):
            stage_complete = True
            next_stage = (
                self.session.query(ECOStage)
                .filter(ECOStage.sequence > stage.sequence)
                .order_by(ECOStage.sequence.asc())
                .first()
            )
            if next_stage and stage.auto_progress:
                eco.stage_id = next_stage.id
                eco.state = ECOState.PROGRESS.value
                self._apply_stage_sla(eco, next_stage)
                self.session.add(eco)
                self.session.flush()
                # P2-2a: auto-assign approvers for the new stage.
                # Only skip when next stage genuinely needs no approval.
                # All other failures (permission, bridge, DB) must propagate
                # so stage doesn't advance with half-built approval state.
                if next_stage.approval_type != "none":
                    self.auto_assign_stage_approvers(eco.id, user_id)
                self.notification_service.notify(
                    "eco.stage_assigned",
                    {
                        "eco_id": eco.id,
                        "stage_id": next_stage.id,
                        "stage_name": next_stage.name,
                        "approval_deadline": eco.approval_deadline.isoformat()
                        if eco.approval_deadline
                        else None,
                    },
                    recipients=self._resolve_stage_recipients(next_stage),
                )
            else:
                eco.state = ECOState.APPROVED.value
                eco.approval_deadline = None
            eco.kanban_state = "normal"
            eco.updated_at = datetime.utcnow()
            self.session.add(eco)
            self.session.flush()
            self._enqueue_eco_updated(
                eco,
                changes={"state": eco.state, "stage_id": eco.stage_id},
            )

        self.audit_service.log_action(
            str(user_id),
            "eco.approve",
            "ECO",
            eco_id,
            details={
                "approval_id": approval.id,
                "stage_id": stage.id,
                "stage_complete": stage_complete,
                "eco_state": eco.state,
                "comment": comment,
            },
        )
        self.notification_service.notify(
            "eco.approved",
            {
                "eco_id": eco_id,
                "approval_id": approval.id,
                "stage_id": stage.id,
                "stage_complete": stage_complete,
                "state": eco.state,
            },
            recipients=self._resolve_stage_recipients(stage),
        )

        return approval

    def reject(self, eco_id: str, user_id: int, comment: str) -> ECOApproval:
        eco = self.session.get(ECO, eco_id)
        if not eco:
            raise ValueError("ECO not found")
        if eco.state == ECOState.SUSPENDED.value:
            raise ValueError("ECO is suspended; unsuspend before rejecting")
        if not eco.stage_id:
            raise ValueError("ECO has no stage assigned")

        stage = self.session.get(ECOStage, eco.stage_id)
        if not stage:
            raise ValueError("ECO stage not found")

        user = self.session.query(RBACUser).filter(RBACUser.id == user_id).first()
        if not self._user_has_stage_role(user, stage):
            raise ValueError("User does not have approval role for this stage")

        approval = (
            self.session.query(ECOApproval)
            .filter_by(eco_id=eco_id, stage_id=stage.id, user_id=user_id)
            .first()
        )
        if not approval:
            approval = ECOApproval(
                id=str(uuid.uuid4()),
                eco_id=eco_id,
                stage_id=stage.id,
                user_id=user_id,
                approval_type="mandatory",
                required_role=None,
                status=ApprovalStatus.PENDING.value,
                comment=None,
            )
            self.session.add(approval)

        approval.status = ApprovalStatus.REJECTED.value
        approval.comment = comment
        approval.approved_at = datetime.utcnow()
        self.session.add(approval)
        self.session.flush()

        eco.state = ECOState.PROGRESS.value
        eco.kanban_state = "blocked"
        eco.updated_at = datetime.utcnow()
        self.session.add(eco)
        self.session.flush()
        self._enqueue_eco_updated(eco, changes={"state": eco.state})

        self.audit_service.log_action(
            str(user_id),
            "eco.reject",
            "ECO",
            eco_id,
            details={
                "approval_id": approval.id,
                "stage_id": stage.id,
                "eco_state": eco.state,
                "comment": comment,
            },
        )
        self.notification_service.notify(
            "eco.rejected",
            {
                "eco_id": eco_id,
                "approval_id": approval.id,
                "stage_id": stage.id,
                "state": eco.state,
            },
            recipients=self._resolve_stage_recipients(stage),
        )

        return approval

    def create_approval(
        self,
        eco_id: str,
        stage_id: str,
        user_id: int,
        approval_type: str = "mandatory",
        required_role: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> ECOApproval:
        self.permission_service.check_permission(user_id, "create", "ECOApproval")

        approval = ECOApproval(
            id=str(uuid.uuid4()),
            eco_id=eco_id,
            stage_id=stage_id,
            user_id=user_id,
            approval_type=approval_type,
            required_role=required_role,
            comment=comment,
            status="pending",  # Initial status
        )
        self.session.add(approval)
        self.session.flush()
        return approval

    def record_approval(
        self,
        eco_id: str,
        stage_id: str,
        user_id: int,
        status: str,  # "approved" or "rejected"
        comment: Optional[str] = None,
    ) -> ECOApproval:
        self.permission_service.check_permission(
            user_id, "execute", "ECOApproval", field="record"
        )

        # Find existing approval or create a new one
        approval = (
            self.session.query(ECOApproval)
            .filter_by(eco_id=eco_id, stage_id=stage_id, user_id=user_id)
            .first()
        )

        if not approval:
            # Create if not exists (e.g., ad-hoc approval)
            approval = self.create_approval(
                eco_id=eco_id,
                stage_id=stage_id,
                user_id=user_id,
                comment=comment,
                approval_type="ad_hoc",  # Mark as ad-hoc
            )

        approval.status = status
        approval.comment = comment
        approval.approved_at = datetime.utcnow()
        self.session.add(approval)
        self.session.flush()

        return approval

    def check_stage_approvals_complete(self, eco_id: str, stage_id: str) -> bool:
        stage = self.session.get(ECOStage, stage_id)
        if not stage or stage.approval_type == "none":
            return True  # No approvals needed

        # Count mandatory approvals
        required_approvals = (
            self.session.query(ECOApproval)
            .filter(
                ECOApproval.eco_id == eco_id,
                ECOApproval.stage_id == stage_id,
                ECOApproval.approval_type == "mandatory",
                ECOApproval.status == "approved",
            )
            .count()
        )

        if required_approvals >= stage.min_approvals:
            return True
        return False

    # ------------------------------------------------------------------
    # P2-2a: Auto-assign stage approvers
    # ------------------------------------------------------------------

    def _resolve_candidate_users(self, stage: ECOStage) -> List[RBACUser]:
        """Resolve active RBAC users whose *active* roles match stage.approval_roles."""
        target_roles = set(stage.approval_roles or [])
        if not target_roles:
            return []
        users = self.session.query(RBACUser).filter(RBACUser.is_active.is_(True)).all()
        result = []
        for u in users:
            if u.is_superuser:
                result.append(u)
                continue
            active_role_names = {
                r.name for r in (u.roles or [])
                if getattr(r, "is_active", True)
            }
            if active_role_names & target_roles:
                result.append(u)
        return result

    def _check_user_eco_permission(self, user_id: int, action: str) -> None:
        """Real RBAC permission check for ECO operations.

        Uses RBACUser.has_permission — not the broken MetaPermissionService()
        instantiated without session.
        """
        user = self.session.query(RBACUser).filter(RBACUser.id == user_id).first()
        if not user:
            from yuantus.exceptions.handlers import PermissionError
            raise PermissionError(
                action=action, resource="ECO",
                details={"reason": f"User {user_id} not found"},
            )
        if user.is_superuser:
            return
        perm_name = f"eco.{action}"
        if not user.has_permission(perm_name):
            from yuantus.exceptions.handlers import PermissionError
            raise PermissionError(
                action=action, resource="ECO",
                details={"reason": f"User {user_id} lacks '{perm_name}' permission"},
            )

    def auto_assign_stage_approvers(self, eco_id: str, user_id: int) -> Dict[str, Any]:
        """Pre-create pending ECOApproval + bridge ApprovalRequest for eligible users.

        Raises:
            PermissionError — user lacks eco.auto_assign permission
            ValueError — ECO not found / no stage / stage does not require approval
        """
        # Fix 1: real RBAC permission check
        self._check_user_eco_permission(user_id, "auto_assign")

        eco = self.session.get(ECO, eco_id)
        if not eco:
            raise ValueError(f"ECO {eco_id} not found")
        if not eco.stage_id:
            raise ValueError(f"ECO {eco_id} has no current stage")

        stage = self.session.get(ECOStage, eco.stage_id)
        if not stage:
            raise ValueError(f"ECO stage {eco.stage_id} not found")
        if stage.approval_type == "none":
            raise ValueError(
                f"Stage '{stage.name}' does not require approval (approval_type=none)"
            )

        candidates = self._resolve_candidate_users(stage)
        if not candidates:
            raise ValueError(
                f"Stage '{stage.name}' requires approval (roles={stage.approval_roles}) "
                f"but no active users with matching active roles were found"
            )
        assigned = []
        ar_ids = []
        newly_assigned_user_ids = []

        for cand in candidates:
            existing = (
                self.session.query(ECOApproval)
                .filter_by(eco_id=eco_id, stage_id=stage.id, user_id=cand.id)
                .first()
            )
            if existing:
                assigned.append({
                    "user_id": cand.id,
                    "username": cand.username,
                    "approval_id": existing.id,
                    "already_existed": True,
                })
                continue

            approval = ECOApproval(
                id=str(uuid.uuid4()),
                eco_id=eco_id,
                stage_id=stage.id,
                user_id=cand.id,
                approval_type="mandatory",
                required_role=None,
                status="pending",
            )
            self.session.add(approval)
            assigned.append({
                "user_id": cand.id,
                "username": cand.username,
                "approval_id": approval.id,
                "already_existed": False,
            })
            newly_assigned_user_ids.append(cand.id)

        self.session.flush()

        # Fix 2: Stage-aware bridge with state check
        # Fix 3: No silent swallow — bridge failures raise and roll back
        from yuantus.meta_engine.approvals.models import ApprovalRequest, ApprovalState
        from yuantus.meta_engine.approvals.service import ApprovalService
        ar_service = ApprovalService(self.session)
        for entry in assigned:
            if entry.get("already_existed"):
                continue
            # Stage-aware dedup: same eco + stage + user
            #   draft → transition to pending, reuse
            #   pending → reuse as-is
            #   approved/rejected/cancelled → create new pending
            existing_ar = (
                self.session.query(ApprovalRequest)
                .filter(
                    ApprovalRequest.entity_type == "eco",
                    ApprovalRequest.entity_id == eco_id,
                    ApprovalRequest.assigned_to_id == entry["user_id"],
                    ApprovalRequest.properties["stage_id"].as_string() == stage.id,
                    ApprovalRequest.state.in_([
                        ApprovalState.DRAFT.value,
                        ApprovalState.PENDING.value,
                    ]),
                )
                .first()
            )
            if existing_ar:
                if existing_ar.state == ApprovalState.DRAFT.value:
                    ar_service.transition_request(existing_ar.id, target_state="pending")
                ar_ids.append(existing_ar.id)
                continue
            # approved/rejected/cancelled or different stage → new
            ar = ar_service.create_request(
                title=f"ECO approval: {eco.name} — stage {stage.name}",
                entity_type="eco",
                entity_id=eco_id,
                priority="normal",
                assigned_to_id=entry["user_id"],
                user_id=eco.created_by_id,
                description=f"stage_id={stage.id}",
            )
            ar.properties = {"stage_id": stage.id, "eco_name": eco.name}
            self.session.add(ar)
            self.session.flush()
            ar_service.transition_request(ar.id, target_state="pending")
            ar_ids.append(ar.id)

        # Fix 4: Notify only newly assigned user IDs, not role bucket
        if newly_assigned_user_ids:
            self.notification_service.notify(
                "eco.approvers_assigned",
                {
                    "eco_id": eco_id,
                    "eco_name": eco.name,
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "assigned_user_ids": newly_assigned_user_ids,
                    "assigned_count": len(newly_assigned_user_ids),
                    "approval_deadline": (
                        eco.approval_deadline.isoformat() if eco.approval_deadline else None
                    ),
                },
                recipients=[str(uid) for uid in newly_assigned_user_ids],
            )

        return {"assigned": assigned, "approval_request_ids": ar_ids}

    # ------------------------------------------------------------------
    # P2-2b: Escalate overdue approvals
    # ------------------------------------------------------------------

    def escalate_overdue_approvals(self, user_id: int) -> Dict[str, Any]:
        """Escalate overdue pending ECO approvals to admin/superuser.

        Raises:
            PermissionError — caller lacks eco.escalate_overdue permission.
        """
        self._check_user_eco_permission(user_id, "escalate_overdue")

        overdue = self.list_overdue_approvals()
        escalated_items = []

        # Resolve escalation targets: active superusers
        admins = (
            self.session.query(RBACUser)
            .filter(RBACUser.is_active.is_(True), RBACUser.is_superuser.is_(True))
            .all()
        )
        if not admins:
            raise ValueError("No active admin/superuser found for escalation")

        from yuantus.meta_engine.approvals.models import ApprovalRequest, ApprovalState
        from yuantus.meta_engine.approvals.service import ApprovalService
        ar_service = ApprovalService(self.session)

        for entry in overdue:
            eco_id = entry["eco_id"]
            stage_id = entry.get("stage_id")
            if not stage_id:
                continue

            eco = self.session.get(ECO, eco_id)
            stage = self.session.get(ECOStage, stage_id) if stage_id else None
            if not eco or not stage:
                continue
            # Fix 2: exclude stages that don't require approval
            if stage.approval_type == "none":
                continue

            pending = (
                self.session.query(ECOApproval)
                .filter_by(eco_id=eco_id, stage_id=stage_id, status="pending")
                .all()
            )
            if not pending:
                continue

            admin_ids = {a.id for a in admins}
            newly_escalated = []

            for admin in admins:
                # Check if admin already has ECOApproval for this eco+stage
                existing_appr = (
                    self.session.query(ECOApproval)
                    .filter_by(eco_id=eco_id, stage_id=stage_id, user_id=admin.id)
                    .first()
                )
                appr_id = None
                if existing_appr:
                    appr_id = existing_appr.id
                else:
                    new_appr = ECOApproval(
                        id=str(uuid.uuid4()),
                        eco_id=eco_id,
                        stage_id=stage_id,
                        user_id=admin.id,
                        approval_type="mandatory",
                        required_role="admin",
                        status="pending",
                    )
                    self.session.add(new_appr)
                    appr_id = new_appr.id

                # Fix 1: Bridge ALWAYS — even when ECOApproval already existed
                existing_ar = (
                    self.session.query(ApprovalRequest)
                    .filter(
                        ApprovalRequest.entity_type == "eco",
                        ApprovalRequest.entity_id == eco_id,
                        ApprovalRequest.assigned_to_id == admin.id,
                        ApprovalRequest.properties["stage_id"].as_string() == stage_id,
                        ApprovalRequest.state.in_([
                            ApprovalState.DRAFT.value,
                            ApprovalState.PENDING.value,
                        ]),
                    )
                    .first()
                )
                if existing_ar:
                    if existing_ar.state == ApprovalState.DRAFT.value:
                        ar_service.transition_request(existing_ar.id, target_state="pending")
                else:
                    ar = ar_service.create_request(
                        title=f"ECO escalation: {eco.name} — stage {stage.name}",
                        entity_type="eco",
                        entity_id=eco_id,
                        priority="urgent",
                        assigned_to_id=admin.id,
                        user_id=user_id,
                        description=f"stage_id={stage_id} escalated",
                    )
                    ar.properties = {"stage_id": stage_id, "eco_name": eco.name, "escalated": True}
                    self.session.add(ar)
                    self.session.flush()
                    ar_service.transition_request(ar.id, target_state="pending")

                if not existing_appr:
                    newly_escalated.append({
                        "escalated_to_user_id": admin.id,
                        "escalated_to_username": admin.username,
                        "approval_id": appr_id,
                    })

            if newly_escalated:
                self.session.flush()
                self.notification_service.notify(
                    "eco.approval_escalated",
                    {
                        "eco_id": eco_id,
                        "eco_name": entry.get("eco_name"),
                        "stage_id": stage_id,
                        "hours_overdue": entry.get("hours_overdue"),
                        "escalated_count": len(newly_escalated),
                    },
                    recipients=[str(e["escalated_to_user_id"]) for e in newly_escalated],
                )
                escalated_items.append({
                    "eco_id": eco_id,
                    "stage_id": stage_id,
                    "hours_overdue": entry.get("hours_overdue"),
                    "escalated": newly_escalated,
                })

        return {"escalated": len(escalated_items), "items": escalated_items}
