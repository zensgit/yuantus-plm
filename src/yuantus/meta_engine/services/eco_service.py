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
from datetime import datetime
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
from yuantus.meta_engine.version.service import VersionService
from yuantus.meta_engine.version.models import ItemVersion
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

    def analyze_impact(self, eco_id: str) -> Dict[str, Any]:
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

        return {
            "eco_id": eco_id,
            "changed_product_id": eco.product_id,
            "impact_count": len(where_used),
            "impacted_assemblies": where_used,
        }

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
        return eco

    def delete_eco(self, eco_id: str, user_id: int):
        # Permission check
        self.permission_service.check_permission(
            user_id, "delete", "ECO", resource_id=eco_id
        )

        eco = self.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO with ID {eco_id} not found.")
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

        # Verify stage exists
        stage = self.session.query(ECOStage).get(stage_id)
        if not stage:
            raise ValueError(f"ECO Stage {stage_id} not found")

        # Update ECO stage
        eco.stage_id = stage_id
        self.session.flush()

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

        return target_version

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
        return eco

    def get_bom_changes(self, eco_id: str) -> List[ECOBOMChange]:
        return (
            self.session.query(ECOBOMChange)
            .filter(ECOBOMChange.eco_id == eco_id)
            .order_by(ECOBOMChange.created_at.asc())
            .all()
        )

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

    def compute_bom_changes(self, eco_id: str) -> List[ECOBOMChange]:
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
        product.updated_at = datetime.utcnow()
        self.session.add(product)

        eco.state = ECOState.DONE.value
        eco.kanban_state = "done"
        eco.product_version_after = target_version.version_label
        eco.updated_at = datetime.utcnow()
        self.session.add(eco)

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

    def get_approval(self, approval_id: str) -> Optional[ECOApproval]:
        return self.session.get(ECOApproval, approval_id)

    def list_approvals_for_eco(self, eco_id: str) -> List[ECOApproval]:
        return self.session.query(ECOApproval).filter_by(eco_id=eco_id).all()

    def get_eco_approvals(self, eco_id: str) -> List[ECOApproval]:
        return self.list_approvals_for_eco(eco_id)

    def _user_has_stage_role(self, user: Optional[RBACUser], stage: ECOStage) -> bool:
        if not stage.approval_roles:
            return True
        if not user:
            return False
        if user.is_superuser:
            return True
        user_role_names = {r.name for r in (user.roles or [])}
        return any(role_name in user_role_names for role_name in (stage.approval_roles or []))

    def get_pending_approvals(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Return a computed list of pending approvals for the given user.

        NOTE: We don't pre-create ECOApproval rows for every user/stage. Instead we
        compute "pending" based on ECO.stage + user roles and existing approval records.
        """
        user = self.session.query(RBACUser).filter(RBACUser.id == user_id).first()

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

            pending.append(
                {
                    "eco_id": eco.id,
                    "eco_name": eco.name,
                    "eco_state": eco.state,
                    "stage_id": stage.id,
                    "stage_name": stage.name,
                    "approval_type": stage.approval_type,
                }
            )

        return pending

    def approve(self, eco_id: str, user_id: int, comment: Optional[str] = None) -> ECOApproval:
        eco = self.session.get(ECO, eco_id)
        if not eco:
            raise ValueError("ECO not found")
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

        # If this stage is complete, progress ECO
        if self.check_stage_approvals_complete(eco_id, stage.id):
            next_stage = (
                self.session.query(ECOStage)
                .filter(ECOStage.sequence > stage.sequence)
                .order_by(ECOStage.sequence.asc())
                .first()
            )
            if next_stage and stage.auto_progress:
                eco.stage_id = next_stage.id
                eco.state = ECOState.PROGRESS.value
            else:
                eco.state = ECOState.APPROVED.value
            eco.kanban_state = "normal"
            eco.updated_at = datetime.utcnow()
            self.session.add(eco)
            self.session.flush()

        return approval

    def reject(self, eco_id: str, user_id: int, comment: str) -> ECOApproval:
        eco = self.session.get(ECO, eco_id)
        if not eco:
            raise ValueError("ECO not found")
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
